#!/usr/bin/env python3
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from threading import Lock
from access_ldb import DatabaseAccess
import access_ldb
import time


# Estimate duration a robot needs to actively handle a job.
ROBOT_JOB_DURATION = timedelta(minutes=1)


class ChargerCommand(IntEnum):
    START_CHARGING = 1
    START_RECHARGING = 2
    STOP_RECHARGING = 3
    RETRIEVE_CHARGER = 4


class JobType(IntEnum):
    BRING_CHARGER = 1
    RETRIEVE_CHARGER = 2
    RECHARGE_CHARGER = 3
    STOW_CHARGER = 4
    RECHARGE_SELF = 5

    def __repr__(self) -> str:
        return self.name


class JobState(IntEnum):
    OPEN = 1
    PENDING = 2
    ONGOING = 3
    COMPLETE = 4

    def __repr__(self) -> str:
        return self.name


def get_list_str_of_dict(entries: Dict[str, str]) -> str:
    return ", ".join(f"{key}: {value}" for key, value in entries.items())


@dataclass
class Job:
    id: int
    state: JobState = field(init=False, default=JobState.OPEN)
    type: JobType
    schedule: datetime
    deadline: Optional[datetime] = None
    booking_id: Optional[int] = None
    robot: Optional[str] = None
    cart: Optional[str] = None
    source_station: Optional[str] = None
    target_station: Optional[str] = None


class Planner:
    def __init__(self) -> None:
        self.access = DatabaseAccess()
        self.env_infos: Dict[str, int] = {}
        self.robot_infos: Dict[str, Dict[str, object]] = {}
        self.update_robot_infos()
        self.cart_infos: Dict[str, Dict[str, object]] = {}
        self.update_cart_infos()
        self.booking_infos: Dict[int, Tuple[str, datetime, datetime, timedelta]] = {}
        self.last_fetched_booking_id = 0
        # Store history of robot jobs.
        self.jobs: List[Job] = []
        # Store which robot is currently performing which job.
        self.current_jobs: Dict[str, Job] = {}
        # Store which cart is currently fulfilling which booking.
        self.current_bookings: Dict[str, int] = {}
        # Store which battery charging station is currently reserved for which cart.
        self.current_reservations: Dict[str, str] = {}
        # Manage currently open jobs, which yet need to be scheduled.
        self.open_jobs: List[Job] = []
        # Manage currently pending jobs, which robots should fetch now.
        self.pending_jobs: Dict[str, Job] = {}
        # Manage currently available robots and carts, which can perform jobs now.
        self.available_robots: List[str] = []
        # TODO Implement availability signal received from chargers.
        self.available_carts: List[str] = list(self.cart_infos.keys())
        self.availability_lock = Lock()
        # Manage currently ready chargers, which expect their next commands.
        self.ready_chargers: Dict[str, ChargerCommand] = {}
        self.active = True
        # Fetch and discard existing bookings from the database for development phase.
        self.fetch_new_bookings()

    def pop_nearest_cart(self, station: str, charge: float) -> Optional[str]:
        """Find nearest available cart to station which can provide charge."""
        # TODO Implement distance and power checks.
        return self.available_carts.pop(0) if self.available_carts else None

    def pop_nearest_robot(self, station: str) -> Optional[str]:
        """Find nearest available robot to station."""
        # TODO Implement distance checks.
        return self.available_robots.pop(0) if self.available_robots else None

    def is_station_occupied(self, station: str) -> bool:
        return any(
            station in infos["cart_location"] for infos in self.cart_infos.values()
        )

    def pop_nearest_station(self, station: str) -> Optional[str]:
        """
        Find nearest available station for a charger,
        preferably a battery charging station, else a battery waiting station.
        """
        # TODO Implement distance checks.
        nearest_station: Optional[str] = None
        for number in range(1, self.env_infos["BCS_count"] + 1):
            station = f"BCS_{number}"
            if not self.is_station_occupied(station):
                nearest_station = station
        if nearest_station is None:
            for number in range(1, self.env_infos["BWS_count"] + 1):
                station = f"BWS_{number}"
                if not self.is_station_occupied(station):
                    nearest_station = station
        return nearest_station

    def update_robot_infos(self) -> None:
        """Update robot infos from ldb."""
        self.robot_infos.update(
            self.access.fetch_by_first_header(
                "robot_info", access_ldb.ROBOT_INFO_HEADERS
            )
        )

    def update_cart_infos(self) -> None:
        """Update cart infos from ldb."""
        self.cart_infos.update(
            self.access.fetch_by_first_header("cart_info", access_ldb.CART_INFO_HEADERS)
        )

    def update_job(self, robot: str) -> None:
        if robot in self.current_jobs.keys():
            job = self.current_jobs[robot]
            del self.current_jobs[robot]
            if job.type in (JobType.BRING_CHARGER, JobType.STOW_CHARGER):
                job = Job(
                    len(self.jobs) + 1,
                    JobType.RECHARGE_SELF,
                    schedule=datetime.now(),
                    robot=robot,
                    source_station="ADS_1",
                    target_station="RBS_1",
                )
                print(f"{job} created.")
                self.jobs.append(job)
            elif job.type == JobType.RECHARGE_SELF:
                print(self.cart_infos["BAT_1"])
                if self.cart_infos["BAT_1"]["cart_location"] == "ADS_1":
                    job = Job(
                        len(self.jobs) + 1,
                        JobType.STOW_CHARGER,
                        schedule=datetime.now(),
                        robot=robot,
                        cart="BAT_1",
                        source_station="ADS_1",
                        target_station="BWS_1",
                    )
                    self.jobs.append(job)

    def fetch_new_bookings(self) -> List[Dict[str, str]]:
        """Fetch new bookings from ldb and initialize new jobs for them."""
        new_bookings = self.access.fetch_new_bookings(
            access_ldb.BOOKING_INFO_HEADERS, self.last_fetched_booking_id
        )
        if new_bookings:
            self.last_fetched_booking_id = max(
                booking["charging_session_id"] for booking in new_bookings
            )
        return new_bookings

    def handle_new_bookings(self) -> None:
        new_bookings = self.fetch_new_bookings()
        for booking in new_bookings:
            print(f"New booking [ {get_list_str_of_dict(booking)} ] received.")
            if all(
                booking[name] is not None
                for name in (
                    "charging_session_id",
                    # "drop_location",
                    "drop_date_time",
                    "pick_up_date_time",
                    "plugintime_calculated",
                )
            ):
                booking_id = int(booking["charging_session_id"])
                target_station = "ADS_1"  # TODO str(booking["drop_location"])
                if not target_station.startswith("ADS_"):
                    target_station = f"ADS_{int(target_station)}"
                # Convert database entry of booking into proper formats.
                drop_date_time = (
                    datetime.strptime(booking["drop_date_time"], "%Y-%m-%d %H:%M:%S")
                    if isinstance(booking["drop_date_time"], str)
                    else booking["drop_date_time"]
                )
                pick_up_date_time = (
                    datetime.strptime(booking["pick_up_date_time"], "%Y-%m-%d %H:%M:%S")
                    if isinstance(booking["pick_up_date_time"], str)
                    else booking["pick_up_date_time"]
                )
                plugintime_calculated = (
                    timedelta(minutes=float(booking["plugintime_calculated"]))
                    if isinstance(booking["plugintime_calculated"], str)
                    else booking["plugintime_calculated"]
                )
                booking_info: Tuple[str, datetime, datetime, timedelta] = (
                    target_station,
                    drop_date_time,
                    pick_up_date_time,
                    plugintime_calculated,
                )
                self.booking_infos[booking_id] = booking_info
                # Create new job for new booking immediately.
                job = Job(
                    len(self.jobs) + 1,
                    JobType.BRING_CHARGER,
                    schedule=drop_date_time,
                    deadline=pick_up_date_time
                    - plugintime_calculated
                    - ROBOT_JOB_DURATION,
                    booking_id=booking_id,
                    target_station=target_station,
                )
                print(f"{job} created.")
                self.jobs.append(job)
                self.open_jobs.append(job)

    def confirm_charger_ready(self, robot: str) -> None:
        """Confirm charger brought and connected by robot as ready."""
        cart = self.current_jobs[robot].cart
        assert (
            cart not in self.ready_chargers.keys()
        ), f"Charger {cart} is already ready."
        self.ready_chargers[cart] = ChargerCommand.START_CHARGING

    def schedule_jobs(self) -> None:
        """Schedule open and due jobs for available robots."""
        with self.availability_lock:
            for job in list(self.open_jobs):
                if not self.available_carts or not self.available_robots:
                    return

                if job.type == JobType.BRING_CHARGER:
                    assert job.booking_id and job.target_station
                    # Select nearest charger to prefer transporting less.
                    cart = self.pop_nearest_cart(
                        job.target_station,
                        self.booking_infos[job.booking_id][-1],
                    )
                    assert cart not in self.current_bookings.keys()
                    source_station = str(self.cart_infos[cart]["cart_location"])
                    # Select nearest robot.
                    robot = self.pop_nearest_robot(source_station)
                    assert robot not in self.current_jobs.keys()
                    job.state = JobState.PENDING  # Transition J1
                    job.robot = robot
                    job.cart = cart
                    job.source_station = source_station
                    self.current_jobs[robot] = job
                    self.pending_jobs[robot] = job
                    self.current_bookings[cart] = job.booking_id  # Transition B1
                elif job.type == JobType.RETRIEVE_CHARGER:
                    assert job.cart and job.source_station
                    robot = self.pop_nearest_robot(job.source_station)
                    assert robot and robot not in self.current_jobs.keys()
                    job.robot = robot
                    target_station = self.pop_nearest_station(
                        self.cart_infos[job.cart]["cart_location"]
                    )
                    assert target_station
                    if target_station.startswith("BCS_"):
                        job.type = JobType.RECHARGE_CHARGER  # Transition J3
                        assert target_station not in self.current_reservations.keys()
                        self.current_reservations[target_station] = job.cart
                        job.target_station = target_station
                    elif target_station.startswith("BWS_"):
                        job.type = JobType.STOW_CHARGER
                        job.target_station = target_station
                    else:
                        raise RuntimeError(f"Invalid target station {target_station}!")

                    assert (
                        job.robot
                        and job.cart
                        and job.source_station
                        and job.target_station
                    )
                    assert job.robot not in self.current_jobs.keys()
                    self.current_jobs[job.robot] = job
                    self.pending_jobs[job.robot] = job
                    job.state = JobState.PENDING
            # Let all remaining available robots recharge themselves.
            for robot in self.available_robots:
                if robot not in self.current_jobs.keys():
                    job = Job(
                        len(self.jobs) + 1,
                        JobType.RECHARGE_SELF,
                        schedule=datetime.now(),
                    )
                    job.state = JobState.PENDING
                    assert robot not in self.pending_jobs.keys()
                    self.current_jobs[robot] = job
                    self.pending_jobs[robot] = job

    def fetch_job(self, robot: str) -> Dict[str, str]:
        """Fetch pending job for robot."""
        if robot in self.pending_jobs.keys():
            job = self.pending_jobs[robot]
            del self.pending_jobs[robot]
            job.state = JobState.ONGOING  # Transition J2 / J4 / J5
            job_details = {
                "job_type": job.type.name,
                "robot_name": robot,
                "cart": job.cart,
                "source_station": job.source_station,
                "target_station": job.target_station,
            }
            print(f"Job [ {get_list_str_of_dict(job_details)} ] sent.")
            self.current_jobs[robot] = job
            return job_details

        # Consider robot trying to fetch a job as available.
        with self.availability_lock:
            if robot not in self.available_robots:
                self.available_robots.append(robot)

        return {
            "job_type": "",
            "robot_name": robot,
            "cart": "",
            "source_station": "",
            "target_station": "",
        }

    def fetch_job_from_keyboard_input(self, robot: str) -> Dict[str, str]:
        job_type = input("Enter job type: ")
        cart = input("Enter cart name: ")
        source_station = input("Enter source_station name: ")
        target_station = input("Enter target_station name: ")

        job_details = {
            "job_type": job_type,
            "robot_name": robot,
            "cart": cart,
            "source_station": source_station,
            "target_station": target_station,
        }
        return job_details

    def run(self, update_interval: float = 1.0) -> None:
        self.env_infos.update(self.access.fetch_env_infos())
        print(
            f"Parking area environment info [ {get_list_str_of_dict(self.env_infos)} ] received."
        )
        while self.active:
            self.update_robot_infos()
            self.update_cart_infos()
            self.handle_new_bookings()
            self.schedule_jobs()
            time.sleep(update_interval)


if __name__ == "__main__":
    Planner().run()
