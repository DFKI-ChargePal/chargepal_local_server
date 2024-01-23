#!/usr/bin/env python3
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from threading import Lock
from access_ldb import DatabaseAccess
import access_ldb
import re
import time


# Estimate duration robot needs to actively handle a job.
ROBOT_JOB_DURATION = timedelta(minutes=1)


class CartCommand(IntEnum):
    START_CHARGING = 1
    START_RECHARGING = 2
    RETRIEVE_CART = 3


class JobType(IntEnum):
    BRING_CHARGER = 1
    RECHARGE_CHARGER = 2
    STOW_CHARGER = 3
    RECHARGE_SELF = 4


class JobState(IntEnum):
    OPEN = 1
    PENDING = 2
    ONGOING = 3
    COMPLETE = 4


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
        self.cart_infos: Dict[str, Dict[str, object]] = {}
        self.booking_infos: Dict[int, Tuple[str, datetime, datetime, timedelta]] = {}
        self.jobs: List[Job] = []
        # Store which robot is currently performing which job.
        self.current_jobs: Dict[str, Job] = {}
        # Store which cart is currently fulfilling which booking.
        self.current_bookings: Dict[str, int] = {}
        # Store which battery charging station is currently reserved for which cart.
        self.current_reservations: Dict[str, str] = {}
        # Manage currently pending jobs, which robots should fetch now.
        self.pending_jobs: Dict[str, Job] = {}
        # Manage currently available robots, which can perform jobs now.
        self.available_robots: List[str] = []
        self.availability_lock = Lock()
        # Manage currently ready carts, which expect their next commands.
        self.ready_carts: Dict[str, CartCommand] = {}
        self.active = True

    def update_robot_infos(self) -> None:
        self.robot_infos.update(
            self.access.fetch_by_first_header(
                "robot_info", access_ldb.ROBOT_INFO_HEADERS
            )
        )

    def update_cart_infos(self) -> None:
        self.cart_infos.update(
            self.access.fetch_by_first_header("cart_info", access_ldb.CART_INFO_HEADERS)
        )

    def handle_new_bookings(self) -> None:
        """Fetch new bookings from ldb and initialize new jobs for them."""
        new_bookings = self.access.fetch_new_bookings(
            access_ldb.BOOKING_INFO_HEADERS,
            max(self.booking_infos.keys()) if self.booking_infos else 0,
        )
        for booking in new_bookings:
            print(f"New booking [ {get_list_str_of_dict(booking)} ] received.")
            booking_id = int(booking["charging_session_id"])
            target_station = booking["drop_location"]
            if not target_station.startswith("ADS_"):
                match_result = re.search(r"0*(\d+)", target_station)
                if match_result:
                    target_station = f"ADS_{match_result.group(1)}"
            drop_date_time = booking["drop_date_time"]
            pick_up_date_time = booking["pick_up_date_time"]
            plugintime_calculated = timedelta(
                minutes=float(booking["plugintime_calculated"])
            )
            booking_info = (
                drop_date_time,
                pick_up_date_time,
                plugintime_calculated,
            )
            self.booking_infos[booking_id] = booking_info

            job = Job(
                len(self.jobs) + 1,
                JobType.BRING_CHARGER,
                drop_date_time,
                pick_up_date_time - plugintime_calculated - ROBOT_JOB_DURATION,
                booking_id,
                target_station=target_station,
            )
            print(f"{job} created.")
            self.jobs.append(job)

    def schedule_jobs(self) -> None:
        """Schedule open and due jobs for available robots."""
        open_jobs = [job for job in self.jobs if job.state == JobState.OPEN]
        if open_jobs and self.available_robots:
            available_carts = [
                cart
                for cart in self.cart_infos.keys()
                if cart not in self.current_bookings.keys()
            ]
            with self.availability_lock:
                while open_jobs and available_carts and self.available_robots:
                    robot = self.available_robots.pop(0)
                    cart = available_carts.pop(0)
                    job = open_jobs.pop(0)
                    job.state = JobState.PENDING  # Transition J1
                    job.robot = robot
                    job.cart = cart
                    job.source_station = self.cart_infos[cart]["cart_location"]
                    self.pending_jobs[robot] = job
                    self.current_bookings[cart] = job.booking_id

    def fetch_job(self, robot_name: str) -> Dict[str, str]:
        if robot_name in self.pending_jobs.keys():
            job = self.pending_jobs[robot_name]
            del self.pending_jobs[robot_name]
            job.state = JobState.ONGOING  # Transition J2
            job_details = {
                "job_type": job.type.name,
                "robot_name": robot_name,
                "cart": job.cart,
                "source_station": job.source_station,
                "target_station": job.target_station,
            }
            print(f"Job [ {get_list_str_of_dict(job_details)} ] sent.")
            return job_details

        # Consider robot with robot_name trying to fetch a job as available.
        with self.availability_lock:
            self.available_robots.append(robot_name)

        return {
            "job_type": "",
            "robot_name": robot_name,
            "cart": "",
            "source_station": "",
            "target_station": "",
        }

    def fetch_job_from_keyboard_input(self, robot_name: str) -> Dict[str, str]:
        job_type = input("Enter job type: ")
        cart = input("Enter cart name: ")
        source_station = input("Enter source_station name: ")
        target_station = input("Enter target_station name: ")

        job_details = {
            "job_type": job_type,
            "robot_name": robot_name,
            "cart": cart,
            "source_station": source_station,
            "target_station": target_station,
        }
        return job_details

    def run(self) -> None:
        self.env_infos.update(self.access.fetch_env_infos())
        print(
            f"Parking area environment info [ {get_list_str_of_dict(self.env_infos)} ] received."
        )
        while self.active:
            self.update_robot_infos()
            self.update_cart_infos()
            self.handle_new_bookings()
            self.schedule_jobs()
            time.sleep(1.0)


if __name__ == "__main__":
    Planner().run()
