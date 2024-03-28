"""
Test script to test planner in custom environments.

The tests use scripts of local server and robot clients with grpc
communication without ROS.
Execution and message polling is accelerated a lot, so the tests
are not suited as real-time tests.
"""

#!/usr/bin/env python3
from typing import Iterable, Optional, Type
from types import TracebackType
from concurrent import futures
from threading import Thread
from chargepal_local_server.communication_pb2 import Response_Job
from chargepal_local_server import communication_pb2_grpc
import grpc
import os
import time
from chargepal_local_server import debug_ldb
from chargepal_local_server.create_ldb_orders import create_sample_booking
from chargepal_local_server.create_pdb import reset_db
from chargepal_local_server.planner import (
    BookingState,
    ChargerCommand,
    JobType,
    Planner,
)
from chargepal_local_server.server import CommunicationServicer
from chargepal_client.core import Core
from pscedev.config import CONFIG_ALL_ONE, CONFIG_DEFAULT
from pscedev.scenario import SCENARIO1
from pscedev import BookingEvent, Config, Event, Monitoring


class Environment:
    def __init__(self, config: Config) -> None:
        self.cwd = os.getcwd()
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        debug_ldb.counts.set(config.counts_str)
        debug_ldb.delete_from("orders_in")
        reset_db()
        # Set all locations to none for entities unused
        #  to prevent them from blocking stations erroneously.
        debug_ldb.update("robot_info SET robot_location = 'NONE'")
        debug_ldb.update("cart_info SET cart_location = 'NONE'")
        debug_ldb.update_locations(config.locations)
        self.robot_clients = {
            f"ChargePal{number}": Core("localhost:55555", f"ChargePal{number}")
            for number in range(1, debug_ldb.counts.robots + 1)
        }
        self.planner: Planner
        self.thread: Thread

    def __enter__(self) -> "Environment":
        os.chdir(os.path.dirname(__file__))
        self.planner = Planner()
        communication_pb2_grpc.add_CommunicationServicer_to_server(
            CommunicationServicer(self.planner), self.server
        )
        self.server.add_insecure_port("[::]:55555")
        self.server.start()
        self.thread = Thread(target=self.planner.run, args=(0.0,))
        self.thread.start()
        return self

    def __exit__(
        self,
        exception_type: Type[BaseException],
        exception_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        os.chdir(self.cwd)
        self.planner.active = False

    def wait_for_next_job(self, timeout: float = 1.0) -> Response_Job:
        """
        With timeout, wait for and return the next job received by any client.

        Note: This is prone to race conditions on purpose.
        """
        time_start = time.time()
        while True:
            for client in self.robot_clients.values():
                response, _ = client.fetch_job()
                assert response, "No response received for grpc request."
                if response.job.job_type:
                    print(response)
                    return response.job
            if time.time() - time_start >= timeout:
                raise TimeoutError("No job.")

    def handle_events(self, events: Iterable[Event]) -> None:
        for event in events:
            if isinstance(event, BookingEvent):
                create_sample_booking(drop_location=event.planned_BEV_location)


def wait_for_job(
    client: Core, job_type: Optional[JobType] = None, timeout: float = 1.0
) -> Response_Job:
    """
    With timeout, wait for client to receive its next job.
    Assert this job is of job_type, then return it.
    """
    time_start = time.time()
    while True:
        response, _ = client.fetch_job()
        if response.job.job_type:
            break
        if time.time() - time_start >= timeout:
            raise TimeoutError("No job.")
    print(response)
    if job_type and response.job.job_type != job_type:
        raise RuntimeError("Wrong job type.")
    return response.job


def test_recharge_self() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        # Test for RECHARGE_SELF job if robot is not at RBS.
        client = environment.robot_clients["ChargePal1"]
        wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")
        environment.planner.update_robot_infos()
        # Test for no job if robot is already at RBS.
        try:
            wait_for_job(client)
            raise RuntimeError("Robot got job but should not have.")
        except TimeoutError:
            pass


def test_bring_and_recharge() -> None:
    monitoring = Monitoring(SCENARIO1)
    with Environment(SCENARIO1.config) as environment:
        client = environment.robot_clients["ChargePal1"]
        # Book and let car appear.
        environment.handle_events(monitoring.get_next_events())
        # Move car to ADS_1.
        monitoring.update_car_at_ads("ADS_1")
        # Check in.
        environment.handle_events(monitoring.get_next_events())
        # Bring BAT_1 to ADS_1.
        job = wait_for_job(client, JobType.BRING_CHARGER)
        assert job.target_station == "ADS_1"
        status = monitoring.get_job_status("BRING_CHARGER", job.target_station)
        assert status == "Success"
        client.update_job_monitor("BRING_CHARGER", status)
        # Recharge ChargePal1.
        wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")
        # Let BAT_1 finish charging.
        debug_ldb.update(
            f"orders_in SET charging_session_status = '{BookingState.FINISHED}'"
        )
        monitoring.update_car_charged("ADS_1")
        # Bring BAT_1 to BCS_1.
        job = wait_for_job(client, JobType.RECHARGE_CHARGER)
        assert job.target_station == "BCS_1"
        status = monitoring.get_job_status("RECHARGE_CHARGER", job.target_station)
        assert status == "Success"
        client.update_job_monitor("RECHARGE_CHARGER", status)
        # Check out.
        environment.handle_events(monitoring.get_next_events())
        assert not monitoring.exists_event()
        # Recharge ChargePal1.
        wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")


def test_failures() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        client = environment.robot_clients["ChargePal1"]
        create_sample_booking(drop_location="ADS_1")
        job = wait_for_job(client, JobType.BRING_CHARGER)
        client.update_job_monitor("BRING_CHARGER", "Failure")
        assert job.cart in environment.planner.available_carts, job.cart
        job = wait_for_job(client, JobType.BRING_CHARGER)
        client.update_job_monitor("BRING_CHARGER", "Success")
        wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Failure")
        wait_for_job(client, JobType.RECHARGE_SELF)
        debug_ldb.update(
            f"orders_in SET charging_session_status = '{BookingState.FINISHED}'"
        )
        client.update_job_monitor("RECHARGE_SELF", "Failure")
        job = wait_for_job(client, JobType.RECHARGE_CHARGER)
        client.update_job_monitor("RECHARGE_CHARGER", "Failure")
        assert job.cart in environment.planner.available_carts, job.cart
        # Note: If recharging charger keeps failing after recovery,
        #  nothing more can be done for it automatically.
        wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")


def test_two_twice_in_parallel() -> None:
    with Environment(CONFIG_DEFAULT) as environment:
        for _ in range(2):
            # Create 2 bookings, let 2 robots bring 2 carts.
            for number in (1, 2):
                create_sample_booking(drop_location=f"ADS_{number}")
            cart1 = environment.wait_for_next_job().cart
            cart2 = environment.wait_for_next_job().cart
            for client in environment.robot_clients.values():
                client.update_job_monitor("BRING_CHARGER", "Success")
            # Let both chargers complete while both robots recharge themselves.
            for _ in range(2):
                environment.wait_for_next_job()
            for charger in (cart1, cart2):
                environment.planner.handle_charger_update(
                    charger, ChargerCommand.BOOKING_FULFILLED
                )
            for client in environment.robot_clients.values():
                client.update_job_monitor("RECHARGE_SELF", "Success")
            # Let robots retrieve the carts, remember the jobs.
            job1 = environment.wait_for_next_job()
            job2 = environment.wait_for_next_job()
            for job in (job1, job2):
                environment.robot_clients[job.robot_name].update_job_monitor(
                    job.job_type, "Success"
                )
            # Stop recharging the chargers which were not stowed,
            #  while both robots recharge themselves.
            for _ in range(2):
                environment.wait_for_next_job()
            for job in (job1, job2):
                assert job.job_type in (
                    "RECHARGE_CHARGER",
                    "STOW_CHARGER",
                ), job.job_type
                if job.job_type == "RECHARGE_CHARGER":
                    environment.planner.handle_charger_update(
                        job.cart, ChargerCommand.STOP_RECHARGING
                    )
            for client in environment.robot_clients.values():
                client.update_job_monitor("RECHARGE_SELF", "Success")


def test_status_update() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        client = environment.robot_clients["ChargePal1"]
        create_sample_booking(
            drop_location="ADS_1", charging_session_status=BookingState.BOOKED
        )
        wait_for_job(environment.robot_clients["ChargePal1"], JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")
        debug_ldb.update(
            f"orders_in SET charging_session_status = '{BookingState.CHECKED_IN}'"
        )
        wait_for_job(environment.robot_clients["ChargePal1"], JobType.BRING_CHARGER)


def test_plug_in_handshake() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        client = environment.robot_clients["ChargePal1"]
        create_sample_booking(drop_location="ADS_1")
        get_status = lambda: debug_ldb.select(
            "charging_session_status FROM orders_in",
        )[-1][0]
        assert get_status() == BookingState.CHECKED_IN, get_status()
        wait_for_job(client, JobType.BRING_CHARGER)
        assert get_status() == BookingState.SCHEDULED, get_status()
        assert not environment.planner.handshake_plug_in("ChargePal1")
        assert get_status() == BookingState.ROBOT_READY_TO_PLUG, get_status()
        assert not environment.planner.handshake_plug_in("ChargePal1")
        debug_ldb.update(
            f"orders_in SET charging_session_status = '{BookingState.BEV_PENDING}'"
            f" WHERE charging_session_status = '{BookingState.ROBOT_READY_TO_PLUG}'"
        )
        assert not environment.planner.handshake_plug_in("ChargePal1")
        environment.planner.handle_updated_bookings()
        time.sleep(1.0)
        assert environment.planner.handshake_plug_in("ChargePal1")


if __name__ == "__main__":
    test_recharge_self()
    test_bring_and_recharge()
    test_failures()
    test_two_twice_in_parallel()
    test_status_update()
    test_plug_in_handshake()
