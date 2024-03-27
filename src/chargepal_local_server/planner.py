"""Rule-based planner for ChargePal robot fleet control"""

#!/usr/bin/env python3
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import IntEnum
from sqlmodel import Session, select
from threading import Lock
from chargepal_local_server import access_ldb
from chargepal_local_server.access_ldb import DatabaseAccess
from chargepal_local_server.pdb_interfaces import Job, engine
import time


# Estimate duration a robot needs to actively handle a job.
ROBOT_JOB_DURATION = timedelta(minutes=1)


class ChargerCommand(IntEnum):
    START_CHARGING = 1
    START_RECHARGING = 2
    STOP_RECHARGING = 3
    RETRIEVE_CHARGER = 4
    BOOKING_FULFILLED = 5


class JobType:
    BRING_CHARGER = "BRING_CHARGER"
    RETRIEVE_CHARGER = "RETRIEVE_CHARGER"
    RECHARGE_CHARGER = "RECHARGE_CHARGER"
    STOW_CHARGER = "STOW_CHARGER"
    RECHARGE_SELF = "RECHARGE_SELF"


class JobState:
    OPEN = "OPEN"
    PENDING = "PENDING"
    ONGOING = "ONGOING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class PlugInState(IntEnum):
    BRING_CHARGER = 1
    ROBOT_READY2PLUG = 2
    BEV_PENDING = 3
    PLUG_IN = 4
    SUCCESS = 5


def get_list_str_of_dict(entries: Dict[str, str]) -> str:
    return ", ".join(f"{key}: {value}" for key, value in entries.items())


class Planner:
    def __init__(self, ldb_filepath: Optional[str] = None) -> None:
        self.access = DatabaseAccess(ldb_filepath)
        self.session = Session(engine)
        self.database_lock = Lock()
        self.env_infos: Dict[str, int] = {}
        self.robot_infos: Dict[str, Dict[str, object]] = {}
        self.update_robot_infos()
        self.cart_infos: Dict[str, Dict[str, object]] = {}
        self.update_cart_infos()
        self.booking_infos: Dict[int, Tuple[str, datetime, datetime, timedelta]] = {}
        self.last_fetched_change = datetime.min
        # Store history of robot jobs.
        # Note: This loads all existing jobs in the database.
        self.jobs: Dict[int, Job] = {
            job.id: job for job in self.session.exec(select(Job)).fetchall()
        }
        self.new_jobs: List[Job] = []
        # Store which cart is currently fulfilling which booking.
        self.current_bookings: Dict[str, int] = {}
        # Store which battery charging station is currently reserved for which cart.
        self.current_reservations: Dict[str, str] = {}
        # Manage currently open bookings, which need a job being created for.
        self.open_bookings: List[int] = []
        # Manage currently available robots and carts, which can perform jobs now.
        self.available_robots: List[str] = []
        # TODO Implement availability signal received from chargers.
        self.available_carts: List[str] = list(self.cart_infos.keys())
        # Manage currently ready chargers, which expect their next commands.
        self.ready_chargers: Dict[str, ChargerCommand] = {}
        self.active = True
        # Manage current states of plug-in jobs for bookings.
        self.plugin_states: Dict[int, PlugInState] = {}
        # Delete existing bookings from the database for development phase.
        self.access.delete_bookings()

    def add_new_job(self, job: Job) -> Job:
        """Add newly created job to all relevant monitoring."""
        if job.state == JobState.PENDING:
            assert (
                job.robot_name is None
                or not self.session.exec(
                    select(Job)
                    .where(Job.robot_name == job.robot_name)
                    .where(Job.state == JobState.PENDING)
                ).first()
            ), f"{job.robot_name} already has a pending job."
        self.session.add(job)
        self.new_jobs.append(job)
        return job

    def get_current_job(self, robot: str) -> Optional[Job]:
        """Return robot's currently assigned job."""
        jobs = self.session.exec(
            select(Job).where(Job.robot_name == robot).where(Job.assigned)
        ).fetchall()
        assert len(jobs) <= 1, f"{robot} has {len(jobs)} assigned."
        return jobs[0] if jobs else None

    def assign_job(self, job: Job, robot: str) -> None:
        """Assign job to robot and update relevant monitoring."""
        assert job.state == JobState.OPEN and robot
        check_job = self.get_current_job(robot)
        assert not check_job, f"{robot} already has job {check_job} assigned."
        job.state = JobState.PENDING
        job.assigned = True
        job.robot_name = robot

    def pop_nearest_cart(self, station: str, charge: float) -> Optional[str]:
        """Find nearest available cart to station which can provide charge."""
        # TODO Implement distance and power checks.
        return self.available_carts.pop(0) if self.available_carts else None

    def pop_nearest_robot(self, station: str) -> Optional[str]:
        """Find nearest available robot to station."""
        # TODO Implement distance checks.
        return self.available_robots.pop(0) if self.available_robots else None

    def is_station_occupied(self, station: str) -> bool:
        """Return whether station is reserved for or used by any cart."""
        return station in self.current_reservations.keys() or any(
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

    def update_job(self, robot: str, job_type: str, job_status: str) -> bool:
        """Update job status."""
        with self.database_lock:
            job = self.get_current_job(robot)
            if not job:
                print(f"Warning: {robot} without current job sent a job update.")
                return False

            print(f"{robot} sends update '{job_status}' for {job}.")
            if job_status == "Success":
                job.state = JobState.COMPLETE  # Transition J9
                job.assigned = False
                assert (
                    job.robot_name and job.robot_name == robot and job.target_station
                ), job
                assert job_type == job.type, (
                    f"{robot} sent update of different job '{job_type}'"
                    f" than its current job '{job.type}'."
                )
                # Update locations of robot and potentially cart.
                if job.target_station in self.current_reservations.keys():
                    assert (
                        self.current_reservations[job.target_station] == job.cart_name
                    ), f"{job.target_station} was not reserved for {job.cart_name}."
                    self.current_reservations.pop(job.target_station)
                self.access.update_location(
                    job.target_station, job.robot_name, job.cart_name
                )
                # Update charging_session_status.
                if job.type == JobType.BRING_CHARGER:
                    self.plugin_states[job.booking_id] = PlugInState.SUCCESS
                    self.access.update_session_status(job.booking_id, "plugin_success")
                elif job.type == JobType.STOW_CHARGER:
                    # Note: Assume cart is always available for development until charger can confirm it in reality.
                    assert job.cart_name not in self.available_carts, job
                    self.available_carts.append(job.cart_name)
                self.session.commit()
                return True
            if job_status == "Failure":
                job.state = JobState.FAILED
                job.assigned = False
                print(f"Warning: {job} for {robot} failed!")
                assert job.robot_name and job.robot_name == robot, (
                    robot,
                    job,
                )
                assert job_type == job.type, (job_type, job)
                if (
                    job.target_station
                    and job.target_station in self.current_reservations.keys()
                ):
                    assert (
                        self.current_reservations[job.target_station] == job.cart_name
                    ), (
                        self.current_reservations,
                        job,
                    )
                    self.current_reservations.pop(job.target_station)
                if job.cart_name:
                    if job.cart_name in self.current_bookings.keys():
                        booking_id = self.current_bookings.pop(job.cart_name)
                        assert booking_id not in self.open_bookings
                        self.open_bookings.append(booking_id)
                    if job.cart_name not in self.available_carts:
                        self.available_carts.append(job.cart_name)
                self.session.commit()
                return True
        if job_status == "Recovery":
            pass
        elif job_status == "Ongoing":
            pass
        raise ValueError(f"Unknown job status: {job_status}")

    def fetch_updated_bookings(self) -> List[Dict[str, object]]:
        """Fetch updated bookings from lsv_db."""
        updated_bookings = self.access.fetch_updated_bookings(
            access_ldb.BOOKING_INFO_HEADERS, self.last_fetched_change
        )
        if updated_bookings:
            self.last_fetched_change = max(
                booking["last_change"] for booking in updated_bookings
            )
        return updated_bookings

    def get_ads_for(self, location: str) -> str:
        """Return adapter station name related to location."""
        if location.startswith("ADS_"):
            return location
        # TODO Remove this workaround when parking area numbering is decided.
        if location[-1].isdigit():
            return f"ADS_{location[-1]}"
        raise ValueError(f"No adapter station mapped to '{location}'.")

    def handle_updated_bookings(self) -> None:
        """Fetch updated bookings from the database and create new jobs from them."""
        updated_bookings = self.fetch_updated_bookings()
        for booking in updated_bookings:
            if all(
                booking[name] is not None
                for name in (
                    "charging_session_id",
                    "drop_location",
                    "drop_date_time",
                    "pick_up_date_time",
                    "plugintime_calculated",
                )
            ):
                booking_id = int(booking["charging_session_id"])
                target_station = self.get_ads_for(booking["drop_location"])
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
                if booking_id not in self.booking_infos.keys():
                    # Remember new booking.
                    booking_info: Tuple[str, datetime, datetime, timedelta] = (
                        target_station,
                        drop_date_time,
                        pick_up_date_time,
                        plugintime_calculated,
                    )
                    self.booking_infos[booking_id] = booking_info
                    assert booking_id not in self.open_bookings
                    self.open_bookings.append(booking_id)  # Transition B0
                if (
                    booking_id in self.open_bookings
                    and booking["charging_session_status"] == "checked_in"
                ):
                    # Create new job for the updated booking.
                    job = self.add_new_job(
                        Job(
                            type=JobType.BRING_CHARGER,
                            state=JobState.OPEN,
                            schedule=drop_date_time,
                            deadline=pick_up_date_time
                            - plugintime_calculated
                            - ROBOT_JOB_DURATION,
                            booking_id=booking_id,
                            assigned=False,
                            target_station=target_station,
                        )
                    )  # Transition J0
                    print(f"{job} created.")
                    self.open_bookings.remove(booking_id)  # Transition B1
                elif booking["charging_session_status"] == "BEV_pending":
                    self.plugin_states[booking_id] = PlugInState.BEV_PENDING
                elif booking["charging_session_status"] == "finished":
                    for cart, check in list(self.current_bookings.items()):
                        if check == booking["charging_session_id"]:
                            self.handle_charger_update(
                                cart, ChargerCommand.BOOKING_FULFILLED
                            )

    def confirm_charger_ready(self, robot: str) -> None:
        """Confirm charger brought and connected by robot as ready."""
        cart = self.get_current_job(robot).cart_name
        assert (
            cart not in self.ready_chargers.keys()
        ), f"Charger {cart} is already ready."
        self.ready_chargers[cart] = ChargerCommand.START_CHARGING

    def handle_charger_update(self, charger: str, command: ChargerCommand) -> None:
        """Handle charger signaling command."""
        if command == ChargerCommand.START_CHARGING:
            pass
        elif command == ChargerCommand.START_RECHARGING:
            pass
        elif command == ChargerCommand.STOP_RECHARGING:
            assert (
                charger not in self.available_carts
            ), f"{charger} was available during recharging."
            self.available_carts.append(charger)
        elif command in (
            ChargerCommand.RETRIEVE_CHARGER,
            ChargerCommand.BOOKING_FULFILLED,
        ):
            assert (
                charger in self.current_bookings.keys()
            ), f"{charger} has no current booking."
            job = self.add_new_job(
                Job(
                    type=JobType.RETRIEVE_CHARGER,
                    state=JobState.OPEN,
                    schedule=datetime.now(),
                    assigned=False,
                    cart_name=charger,
                    source_station=self.booking_infos[self.current_bookings[charger]][
                        0
                    ],
                )
            )  # Transition J0
            print(f"{job} created.")
            self.current_bookings.pop(charger)  # Transition B2

    def schedule_jobs(self) -> None:
        """Schedule open and due jobs for available robots."""
        for job in self.session.exec(
            select(Job).where(Job.state == JobState.OPEN)
        ).fetchall():
            if not self.available_robots:
                return

            if job.type == JobType.BRING_CHARGER:
                if not self.available_carts:
                    continue

                assert job.booking_id and job.target_station
                # Select nearest cart to prefer transporting less.
                cart = self.pop_nearest_cart(
                    job.target_station,
                    self.booking_infos[job.booking_id][-1],
                )
                assert (
                    cart not in self.current_bookings.keys()
                ), f"{cart} is already used for {self.current_bookings[cart]}."
                source_station = str(self.cart_infos[cart]["cart_location"])
                robot = self.pop_nearest_robot(source_station)
                self.assign_job(job, robot)  # Transition J1
                job.cart_name = cart
                job.source_station = source_station
                self.current_bookings[cart] = job.booking_id
                self.plugin_states[job.booking_id] = PlugInState.BRING_CHARGER
            elif job.type == JobType.RETRIEVE_CHARGER:
                assert job.cart_name and job.source_station
                robot = self.pop_nearest_robot(job.source_station)
                target_station = self.pop_nearest_station(
                    self.cart_infos[job.cart_name]["cart_location"]
                )
                # Note: In a real setup, there should always exist at least a BWS as target_station.
                if target_station:
                    self.assign_job(job, robot)  # Transition J3
                    if target_station.startswith("BCS_"):
                        job.type = JobType.RECHARGE_CHARGER
                        assert (
                            target_station not in self.current_reservations.keys()
                        ), f"{target_station} is already reserved for {self.current_reservations[target_station]}."
                        self.current_reservations[target_station] = job.cart_name
                        job.target_station = target_station
                    elif target_station.startswith("BWS_"):
                        job.type = JobType.STOW_CHARGER
                        job.target_station = target_station
                    else:
                        raise RuntimeError(f"Invalid target station {target_station}!")
                    assert (
                        job.robot_name
                        and job.cart_name
                        and job.source_station
                        and job.target_station
                    )
                else:
                    print("Warning: No station available.")
        # Let all remaining available robots not at RBS recharge themselves.
        for robot in list(self.available_robots):
            check_job = self.get_current_job(robot)
            robot_location: str = self.robot_infos[robot]["robot_location"]
            if not check_job and not robot_location.startswith("RBS_"):
                assert robot.startswith("ChargePal")
                job = self.add_new_job(
                    Job(
                        type=JobType.RECHARGE_SELF,
                        state=JobState.PENDING,
                        schedule=datetime.now(),
                        assigned=True,
                        robot_name=robot,
                        target_station=f"RBS_{robot[9:]}",
                    )
                )  # Transition J0 + J1
                self.available_robots.remove(robot)

    def fetch_job(self, robot: str) -> Dict[str, str]:
        """Fetch pending job for robot."""
        with self.database_lock:
            job = self.get_current_job(robot)
            if job and job.state == JobState.PENDING:
                job.state = JobState.ONGOING  # Transition J2
                job_details = {
                    "job_type": job.type,
                    "robot_name": robot,
                    "cart": job.cart_name,
                    "source_station": job.source_station,
                    "target_station": job.target_station,
                }
                print(f"Job {job.id} [ {get_list_str_of_dict(job_details)} ] sent.")
                self.session.commit()
                return job_details

            # Consider robot trying to fetch a job as available.
            if (
                robot not in self.available_robots
                # For robustness, make sure the current job has been cleared.
                and not job
            ):
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

    def robot_ready2plug(self, robot: str) -> bool:
        booking_id = self.get_current_job(robot).booking_id
        plugin_state = self.plugin_states[booking_id]
        if plugin_state == PlugInState.BRING_CHARGER:
            self.plugin_states[booking_id] = PlugInState.ROBOT_READY2PLUG
            self.access.update_session_status(booking_id, "robot_ready2plug")
        elif plugin_state == PlugInState.BEV_PENDING:
            self.plugin_states[booking_id] = PlugInState.PLUG_IN
            return True
        return False

    def run(self, update_interval: float = 1.0) -> None:
        self.env_infos.update(self.access.fetch_env_infos())
        print(
            f"Parking area environment info [ {get_list_str_of_dict(self.env_infos)} ] received."
        )
        while self.active:
            with self.database_lock:
                self.update_robot_infos()
                self.update_cart_infos()
                self.handle_updated_bookings()
                self.schedule_jobs()
                self.session.commit()
                # Note: Access auto-generated primary key after commit.
                for job in self.new_jobs:
                    assert job.id, f"{job} has no id."
                    self.jobs[job.id] = job
                self.new_jobs.clear()
            time.sleep(update_interval)


if __name__ == "__main__":
    planner = Planner()
    try:
        planner.run()
    except AssertionError:
        planner.session.commit()
