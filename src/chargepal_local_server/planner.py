"""Rule-based planner for ChargePal robot fleet control"""

#!/usr/bin/env python3
from typing import Callable, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import IntEnum
from sqlmodel import Session, select
from chargepal_local_server.access_ldb import LDB
from chargepal_local_server.battery_communication import UpdateManager
from chargepal_local_server.free_station import search_free_station
from chargepal_local_server.layout import Layout
from chargepal_local_server.pdb_interfaces import (
    Booking,
    Cart,
    Job,
    Robot,
    Station,
    pdb_engine,
)
from chargepal_local_server.update_pdb import copy_from_ldb, fetch_updated_bookings
import logging
import time


# Estimate duration a robot needs to actively handle a job.
ROBOT_JOB_DURATION = timedelta(minutes=1)


class ChargerCommand(IntEnum):
    START_CHARGING = 1
    START_RECHARGING = 2
    STOP_RECHARGING = 3
    RETRIEVE_CHARGER = 4
    BOOKING_FULFILLED = 5


class BookingState:
    BOOKED = "booked"
    CHECKED_IN = "checked_in"
    # Note: Not yet implemented in LSV.
    # SCHEDULED = "scheduled"
    # ROBOT_READY_TO_PLUG = "robot_ready2plug"
    PENDING = "pending"
    CHARGING_BEV = "charging_BEV"
    READY = "ready"
    CANCELED = "canceled"
    NO_SHOW = "no_show"

    def equals(state1: str, state2: str) -> bool:
        return state1.lower() == state2.lower()


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
    CANCELED = "CANCELED"


class PlugInState(IntEnum):
    BRING_CHARGER = 1
    ROBOT_READY2PLUG = 2
    BEV_PENDING = 3
    PLUG_IN = 4
    SUCCESS = 5


def get_list_str_of_dict(entries: Dict[str, str]) -> str:
    return ", ".join(f"{key}: {value}" for key, value in entries.items())


class Planner:
    def __init__(self) -> None:
        self.session = Session(pdb_engine)
        self.battery_manager = UpdateManager(
            {f"BAT_{number}": f"Battery_DUS_{number:02d}" for number in range(1, 7)}
        )
        self.robot_count = len(self.session.exec(select(Robot)).fetchall())
        carts = self.session.exec(select(Cart)).fetchall()
        self.cart_count = len(carts)
        self.stations = list(self.session.exec(select(Station)).fetchall())
        self.ADS_count, self.BCS_count, self.BWS_count, self.RBS_count = [
            sum(
                1
                for station in self.stations
                if station.station_name.startswith(prefix)
            )
            for prefix in ("ADS_", "BCS_", "BWS_", "RBS_")
        ]
        self.layout = Layout()
        self.active = True
        # Manage currently ready chargers, which expect their next commands.
        self.ready_chargers: Dict[str, ChargerCommand] = {}
        # Manage current states of plug-in jobs for bookings.
        self.plugin_states: Dict[int, PlugInState] = {}
        # Delete existing bookings from the database for development phase.
        LDB.delete_bookings()
        # Store whether planner received updated bookings.
        self.bookings_updated = False
        # Store job requests from job for synchroneous handling.
        self.job_requests: List[Tuple[Callable[..., object], Tuple[str, ...]]] = []
        # Maintain jobs to be fetched by robots.
        self.next_jobs: Dict[str, object] = {}

    def get_robot(self, name: str) -> Robot:
        """Return robot with name."""
        return self.session.exec(select(Robot).where(Robot.name == name)).first()

    def get_available_robots(self) -> List[Robot]:
        """Return list of available robots."""
        return list(self.session.exec(select(Robot).where(Robot.available)).fetchall())

    def get_cart(self, name: str) -> Cart:
        """Return cart with name."""
        return self.session.exec(select(Cart).where(Cart.name == name)).first()

    def get_available_carts(self) -> List[Cart]:
        """Return list of available carts."""
        return list(self.session.exec(select(Cart).where(Cart.available)).fetchall())

    def get_station(self, name: str) -> Station:
        """Return station with name."""
        return self.session.exec(
            select(Station).where(Station.station_name == name)
        ).first()

    def get_booking(self, booking_id: int) -> Booking:
        """Return booking with booking_id."""
        return self.session.exec(
            select(Booking).where(Booking.id == booking_id)
        ).first()

    def get_current_job(self, robot_name: str) -> Optional[Job]:
        """Return robot's currently assigned job."""
        jobs = self.session.exec(
            select(Job)
            .where(Job.robot_name == robot_name)
            .where(Job.currently_assigned)
        ).fetchall()
        assert len(jobs) <= 1, f"{robot_name} has {len(jobs)} assigned."
        return jobs[0] if jobs else None

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
        return job

    def assign_job(self, job: Job, robot_name: str) -> None:
        """Assign job to robot and update relevant monitoring."""
        assert job.state == JobState.OPEN and robot_name, job
        check_job = self.get_current_job(robot_name)
        assert not check_job, f"{robot_name} already has job {check_job} assigned."
        job.state = JobState.PENDING
        job.currently_assigned = True
        job.robot_name = robot_name
        logging.debug(f"{job} assigned to {robot_name}.")

    def cancel_job(self, job: Job) -> None:
        """Cancel job and clear referenced resources."""
        job.state = JobState.CANCELED
        job.currently_assigned = False
        if job.robot_name:
            robot = self.get_robot(job.robot_name)
            robot.current_job = None
            robot.current_job_id = None
            robot.available = True
            job.robot_name = None
            print("--", robot)
        if job.cart_name:
            cart = self.get_cart(job.cart_name)
            cart.booking_id = None
            cart.available = True
            job.cart_name = None
        if job.target_station:
            station = self.get_station(job.target_station)
            station.reservation = None
            station.available = True

    def pop_nearest_cart(self, location: str, charge: float) -> Optional[Cart]:
        """Find nearest available cart to location which can provide charge."""
        available_carts = self.get_available_carts()
        cart: Optional[Cart] = None
        best_distance = float("inf")
        while available_carts:
            check = available_carts.pop(0)
            if check.cart_charge >= charge:
                distance = self.layout.get_distance(check.cart_location, location)
                if distance < best_distance:
                    cart = check
                    best_distance = distance
        if cart:
            cart.available = False
        return cart

    def pop_nearest_robot(self, location: str) -> Optional[Robot]:
        """Find nearest available robot to location."""
        available_robots = self.get_available_robots()
        robot: Optional[Robot] = None
        best_distance = float("inf")
        while available_robots:
            check = available_robots.pop(0)
            distance = self.layout.get_distance(check.robot_location, location)
            if distance < best_distance:
                robot = check
                best_distance = distance
        if robot:
            robot.available = False
        return robot

    def is_station_occupied(self, station_name: str) -> bool:
        """Return whether station is reserved for or used by any cart."""
        cart_locations = self.session.exec(select(Cart.cart_location)).fetchall()
        return self.get_station(station_name).reservation or any(
            station_name in cart_location for cart_location in cart_locations
        )

    def pop_nearest_station(self, location: str) -> Optional[Station]:
        """Find nearest available battery charging station to location."""
        available_stations = [
            station
            for station in self.stations
            if station.station_name.startswith("BCS_")
        ]
        station: Optional[Station] = None
        best_distance = float("inf")
        while available_stations:
            check = available_stations.pop(0)
            if not self.is_station_occupied(check.station_name):
                distance = self.layout.get_distance(check.station_name, location)
                if distance < best_distance:
                    station = check
                    best_distance = distance
        return station

    def update_job(self, robot_name: str, job_type: str, job_status: str) -> bool:
        """Queue asynchronous update job request."""
        self.job_requests.append(
            (
                self.handle_update_job,
                (
                    robot_name,
                    job_type,
                    job_status,
                ),
            )
        )
        return True

    def handle_update_job(
        self, robot_name: str, job_type: str, job_status: str
    ) -> bool:
        """Update job status."""
        job = self.get_current_job(robot_name)
        if not job:
            logging.warning(
                f"Warning: {robot_name} without current job sent a job update."
            )
            return False

        logging.info(f"{robot_name} sends update '{job_status}' for {job}.")
        if job_status == "Success":
            assert job.robot_name == robot_name, (job, robot_name)
            job.state = JobState.COMPLETE  # Transition J9
            job.currently_assigned = False
            job.robot_name = None
            logging.debug(f"{job} for {robot_name} complete.")
            assert job_type == job.type, (
                f"{robot_name} sent update of different job '{job_type}'"
                f" than its current job '{job.type}'."
            )
            if job.source_station:
                # Make source station available again.
                station = self.get_station(job.source_station)
                station.available = True
            # Update locations of robot and potentially cart.
            assert job.target_station
            station = self.get_station(job.target_station)
            if station.reservation:
                assert (
                    station.reservation == job.cart_name
                ), f"{station} was not reserved for {job.cart_name}."
                station.reservation = None
            LDB.update_location(job.target_station, robot_name, job.cart_name)
            # Update charging_session_status.
            if job.type == JobType.BRING_CHARGER:
                self.plugin_states[job.booking_id] = PlugInState.SUCCESS
                # Note: Update charging_session_status when corresponding status is implemented.
            elif job.type == JobType.STOW_CHARGER:
                # Note: Assume cart is always available for development
                #  until charger can confirm it in reality.
                cart = self.get_cart(job.cart_name)
                cart.available = True
                # Note: In a real setup, there should always exist a BCS.
                if self.BCS_count > 0:
                    # Immediately create a recharge job for cart.
                    new_job = self.add_new_job(
                        Job(
                            type=JobType.RECHARGE_CHARGER,
                            state=JobState.OPEN,
                            schedule=datetime.now(),
                            currently_assigned=False,
                            cart_name=cart.name,
                            source_station=cart.cart_location,
                        )
                    )
                    logging.info(f"{new_job} created.")
            return True
        if job_status == "Failure":
            logging.warning(f"Warning: {job} for {robot_name} failed!")
            assert job.robot_name == robot_name, (job, robot_name)
            job.state = JobState.FAILED
            job.currently_assigned = False
            job.robot_name = None
            assert job_type == job.type, (job_type, job)
            if job.target_station:
                station = self.get_station(job.target_station)
                if station.reservation:
                    assert station.reservation == job.cart_name, job
                    station.reservation = None
            if job.cart_name:
                cart = self.get_cart(job.cart_name)
                if cart.booking_id:
                    booking = self.get_booking(cart.booking_id)
                    assert not BookingState.equals(
                        booking.charging_session_status, BookingState.CHECKED_IN
                    ), booking
                    booking.charging_session_status = BookingState.CHECKED_IN
                    LDB.update_session_status(cart.booking_id, BookingState.CHECKED_IN)
                    cart.booking_id = None
                    logging.debug(f"{booking} reset to checked-in.")
                cart = self.get_cart(job.cart_name)
                if not cart.available:
                    cart.available = True
            return True
        if job_status == "Recovery":
            pass
        elif job_status == "Ongoing":
            pass
        raise ValueError(f"Unknown job status: {job_status}")

    def get_ads_for(self, location: str) -> str:
        """Return adapter station name related to location."""
        if location.startswith("ADS_"):
            return location
        # TODO Remove this workaround when parking area numbering is decided.
        if location[-1].isdigit():
            return f"ADS_{location[-1]}"
        raise ValueError(f"No adapter station mapped to '{location}'.")

    def handle_updated_bookings(self) -> bool:
        """
        Fetch updated bookings from the database and create new jobs for new bookings.
        Return whether there were updated bookings.
        """
        updated_bookings = fetch_updated_bookings()  # Transition B0
        for booking_id, booking in updated_bookings.items():
            target_station = self.get_ads_for(booking.actual_BEV_location)
            if not target_station.startswith("ADS_"):
                target_station = f"ADS_{int(target_station)}"
            booking = self.get_booking(booking_id)
            if BookingState.equals(
                booking.charging_session_status, BookingState.CHECKED_IN
            ):
                # Create new job for the updated booking.
                actual_BEV_pickup_time = (
                    booking.actual_BEV_pickup_time
                    if booking.actual_BEV_pickup_time
                    else booking.actual_BEV_drop_time + timedelta(hours=2.0)
                )
                job = self.add_new_job(
                    Job(
                        type=JobType.BRING_CHARGER,
                        state=JobState.OPEN,
                        schedule=booking.actual_BEV_drop_time,
                        deadline=actual_BEV_pickup_time
                        - booking.actual_plugintime_calculated
                        - ROBOT_JOB_DURATION,
                        booking_id=booking_id,
                        currently_assigned=False,
                        target_station=target_station,
                        charging_type=booking.BEV_slot_planned,
                        port_location=booking.BEV_port_location,
                    )
                )  # Transition J0
                logging.info(f"{job} created.")
                # Note: Use BOOKED as workaround for missing status SCHEDULED.
                booking.charging_session_status = BookingState.BOOKED
                LDB.update_session_status(
                    booking_id, booking.charging_session_status
                )  # Transition B1
                logging.debug(f"{booking} scheduled.")
            elif BookingState.equals(
                booking.charging_session_status, BookingState.PENDING
            ):
                self.plugin_states[booking_id] = PlugInState.BEV_PENDING
            elif BookingState.equals(
                booking.charging_session_status, BookingState.READY
            ):
                cart = self.session.exec(
                    select(Cart).where(Cart.booking_id == booking.id)
                ).first()
                if cart:
                    self.handle_charger_update(cart, ChargerCommand.BOOKING_FULFILLED)
            elif BookingState.equals(
                booking.charging_session_status, BookingState.CANCELED
            ):
                jobs = self.session.exec(
                    select(Job).where(Job.booking_id == booking.id)
                ).fetchall()
                for job in jobs:
                    if job.state in (JobState.OPEN, JobState.PENDING):
                        logging.info(f"{job} canceled due to canceled booking.")
                        self.cancel_job(job)
                    elif job.state == JobState.ONGOING:
                        logging.warning(
                            f"Ongoing {job} canceled due to canceled booking."
                        )
                        self.cancel_job(job)
                    elif job.state != JobState.CANCELED:
                        logging.warning(f"Cannot cancel {job}.")
        return bool(updated_bookings)

    def confirm_charger_ready(self, robot_name: str) -> None:
        """Confirm charger brought and connected by robot as ready."""
        cart_name = self.get_current_job(robot_name).cart_name
        assert (
            cart_name not in self.ready_chargers.keys()
        ), f"Charger {cart_name} is already ready."
        self.ready_chargers[cart_name] = ChargerCommand.START_CHARGING
        self.session.commit()

    def handle_charger_update(self, cart: Cart, command: ChargerCommand) -> None:
        """Handle charger signaling command."""
        if command == ChargerCommand.START_CHARGING:
            pass
        elif command == ChargerCommand.START_RECHARGING:
            pass
        elif command == ChargerCommand.STOP_RECHARGING:
            assert not cart.available, f"{cart} was available during recharging."
            cart.available = True
            if self.session.exec(
                select(Job)
                .where(Job.type == JobType.RECHARGE_CHARGER)
                .where(Job.state == JobState.OPEN)
            ).first():
                new_job = self.add_new_job(
                    Job(
                        type=JobType.STOW_CHARGER,
                        state=JobState.OPEN,
                        schedule=datetime.now(),
                        currently_assigned=False,
                        cart_name=cart.name,
                        source_station=cart.cart_location,
                    )
                )
                logging.info(f"{new_job} created.")
        elif command in (
            ChargerCommand.RETRIEVE_CHARGER,
            ChargerCommand.BOOKING_FULFILLED,
        ):
            assert cart.booking_id, f"{cart} has no current booking."
            booking = self.get_booking(cart.booking_id)
            job = self.add_new_job(
                Job(
                    type=JobType.RETRIEVE_CHARGER,
                    state=JobState.OPEN,
                    schedule=datetime.now(),
                    currently_assigned=False,
                    cart_name=cart.name,
                    source_station=booking.actual_BEV_location,
                    charging_type=booking.BEV_slot_planned,
                    port_location=booking.BEV_port_location,
                )
            )  # Transition J0
            logging.info(f"{job} created.")
            cart.booking_id = None  # Transition B2
        self.session.commit()

    def handle_updated_battery_states(
        self, updated_battery_states: Dict[str, str]
    ) -> None:
        for cart_name, state in updated_battery_states.items():
            cart = self.get_cart(cart_name)
            if "_charging" in state.lower():
                self.handle_charger_update(cart, ChargerCommand.START_CHARGING)
            elif "_recharging" in state.lower():
                self.handle_charger_update(cart, ChargerCommand.START_RECHARGING)
            elif "_charging" in self.battery_manager.battery_states[cart_name]:
                self.handle_charger_update(cart, ChargerCommand.RETRIEVE_CHARGER)
            elif "_recharging" in self.battery_manager.battery_states[cart_name]:
                self.handle_charger_update(cart, ChargerCommand.STOP_RECHARGING)

    def schedule_jobs(self) -> None:
        """Schedule open and due jobs for available robots."""
        for job in self.session.exec(
            select(Job).where(Job.state == JobState.OPEN)
        ).fetchall():
            if not self.get_available_robots():
                return

            if job.type == JobType.BRING_CHARGER:
                assert job.booking_id and job.target_station, job
                if (
                    self.is_station_occupied(job.target_station)
                    or not self.get_available_carts()
                ):
                    continue

                # Select nearest cart to prefer transporting less.
                cart = self.pop_nearest_cart(
                    job.target_station,
                    self.get_booking(job.booking_id).actual_charge_request,
                )
                if cart:
                    assert (
                        cart.booking_id is None
                    ), f"{cart} is already used for {self.get_booking(cart.booking_id)}."
                    robot = self.pop_nearest_robot(cart.cart_location)
                    if robot:
                        self.assign_job(job, robot.name)  # Transition J1
                        job.cart_name = cart.name
                        job.source_station = cart.cart_location
                        self.get_station(job.target_station).available = False
                        cart.booking_id = job.booking_id
                        self.plugin_states[job.booking_id] = PlugInState.BRING_CHARGER
            elif job.type == JobType.RETRIEVE_CHARGER:
                # Handle job to retrieve charger from adapter station.
                assert job.cart_name and job.source_station, job
                robot = self.pop_nearest_robot(job.source_station)
                assert robot, job
                target_station = self.pop_nearest_station(
                    self.get_cart(job.cart_name).cart_location
                )
                if not target_station:
                    target_station = self.get_station(
                        search_free_station(robot.name, "BWS_")
                    )
                # Note: In a real setup, there should always exist at least a BWS as target_station.
                assert target_station, "No target station available."
                target_station.available = False
                self.assign_job(job, robot.name)  # Transition J3
                if target_station.station_name.startswith("BCS_"):
                    job.type = JobType.RECHARGE_CHARGER
                    assert (
                        target_station.reservation is None
                    ), f"{target_station} is already reserved."
                    target_station.reservation = job.cart_name
                    job.target_station = target_station.station_name
                elif target_station.station_name.startswith("BWS_"):
                    job.type = JobType.STOW_CHARGER
                    job.target_station = target_station.station_name
                else:
                    raise RuntimeError(f"Invalid target station {target_station}!")
                assert (
                    job.robot_name
                    and job.cart_name
                    and job.source_station
                    and job.target_station
                ), job
            elif job.type == JobType.STOW_CHARGER:
                # Handle job to recharger charger at battery waiting station.
                assert job.cart_name and job.source_station, job
                robot = self.pop_nearest_robot(job.source_station)
                assert robot, job
                target_station = self.get_station(
                    search_free_station(robot.name, "BWS_")
                )
                target_station.available = False
                job.target_station = target_station.station_name
                self.assign_job(job, robot.name)
            elif job.type == JobType.RECHARGE_CHARGER:
                # Handle job to stow charger at battery charging station.
                assert job.cart_name and job.source_station, job
                target_station = self.pop_nearest_station(job.source_station)
                if target_station:
                    assert target_station.station_name.startswith("BCS_")
                    target_station.available = False
                    job.target_station = target_station.station_name
                    robot = self.pop_nearest_robot(job.source_station)
                    assert robot, job
                    self.assign_job(job, robot.name)
        # Let all remaining available robots not at RBS recharge themselves.
        available_robots = self.get_available_robots()
        for robot in available_robots:
            check_job = self.get_current_job(robot.name)
            if not check_job and not robot.robot_location.startswith("RBS_"):
                job = self.add_new_job(
                    Job(
                        type=JobType.RECHARGE_SELF,
                        state=JobState.PENDING,
                        schedule=datetime.now(),
                        currently_assigned=True,
                        robot_name=robot.name,
                        target_station=f"RBS_{robot.name[9:]}",
                    )
                )  # Transition J0 + J1
                logging.debug(f"{job} created.")
                robot.available = False

    def fetch_job(self, robot_name: str) -> Dict[str, str]:
        """Queue asynchronous fetch job request."""
        self.job_requests.append((self.handle_fetch_job, (robot_name,)))
        if robot_name in self.next_jobs.keys():
            return self.next_jobs.pop(robot_name)

        return {
            "job_id": 0,
            "job_type": "",
            "charging_type": "",
            "robot_name": robot_name,
            "cart": "",
            "source_station": "",
            "target_station": "",
        }

    def handle_fetch_job(self, robot_name: str) -> None:
        """Handle request to fetch pending job for robot with robot_name."""
        job = self.get_current_job(robot_name)
        if job and job.state == JobState.PENDING:
            job.state = JobState.ONGOING  # Transition J2
            job_details = {
                "job_id": job.id,
                "job_type": job.type,
                "charging_type": job.charging_type,
                "robot_name": robot_name,
                "cart": job.cart_name,
                "source_station": job.source_station,
                "target_station": job.target_station,
            }
            logging.info(
                f"Job {job.id} [ {get_list_str_of_dict(job_details)} ] prepared."
            )
            self.next_jobs[robot_name] = job_details
            return

        # Consider robot trying to fetch a job as available.
        robot = self.get_robot(robot_name)
        # Make robot available only after it is cleared from its previous job.
        if not robot.available and not job:
            robot.available = True

    def handshake_plug_in(self, robot_name: str) -> bool:
        booking_id = self.get_current_job(robot_name).booking_id
        booking = self.get_booking(booking_id)
        plugin_state = self.plugin_states[booking_id]
        if plugin_state == PlugInState.BRING_CHARGER:
            self.plugin_states[booking_id] = PlugInState.ROBOT_READY2PLUG
            # Note: Use PENDING as workaround for missing status ROBOT_READY_TO_PLUG.
            LDB.update_session_status(booking_id, BookingState.PENDING)
            logging.debug(f"{booking}'s robot is ready to plug.")
        elif plugin_state == PlugInState.BEV_PENDING:
            self.plugin_states[booking_id] = PlugInState.PLUG_IN
            return True
        return False

    def handle_job_requests(self) -> None:
        """Handle queued job requests."""
        while self.job_requests:
            callback, args = self.job_requests.pop()
            callback(*args)

    def tick(self) -> None:
        """Execute planning methods once."""
        self.bookings_updated = False
        copy_from_ldb()
        self.bookings_updated = self.handle_updated_bookings()
        updated_battery_states = self.battery_manager.tick()
        self.handle_updated_battery_states(updated_battery_states)
        self.schedule_jobs()
        self.handle_job_requests()
        self.session.commit()

    def run(self, update_interval: float = 1.0) -> None:
        logging.basicConfig(level=logging.DEBUG)
        logging.info(
            f"robot_count: {self.robot_count}, cart_count: {self.cart_count}, ADS_count: {self.ADS_count},"
            f" BCS_count: {self.BCS_count}, BWS_count: {self.BWS_count}, RBS_count: {self.RBS_count}"
        )
        while self.active:
            self.tick()
            time.sleep(update_interval)


if __name__ == "__main__":
    planner = Planner()
    try:
        planner.run()
    except AssertionError:
        planner.session.commit()
