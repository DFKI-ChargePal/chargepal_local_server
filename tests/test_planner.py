#!/usr/bin/env python3
"""
Test script to test planner in custom environments.

The tests use scripts of local server and robot clients with grpc
communication without ROS.
Execution and message polling is accelerated a lot, so the tests
are not suited as real-time tests.
"""

from typing import Iterable, Optional, Type
from types import TracebackType
from concurrent import futures
from chargepal_local_server.communication_pb2 import Response_Job
from chargepal_local_server import communication_pb2_grpc
import grpc
import logging
import os
import time
from chargepal_local_server import create_ldb, debug_sqlite_db
from chargepal_local_server.access_ldb import LDB
from chargepal_local_server.create_ldb_orders import create_sample_booking
from chargepal_local_server.create_pdb import initialize_db
from chargepal_local_server.planner import (
    BookingState,
    ChargerCommand,
    JobType,
    Planner,
)
from chargepal_local_server.pscedev.config import CONFIG_ALL_ONE, CONFIG_DEFAULT
from chargepal_local_server.pscedev.scenario import SCENARIO2
from chargepal_local_server.pscedev import BookingEvent, Config, Event, Monitoring
from chargepal_local_server.server import CommunicationServicer
from chargepal_client.core import Core


class Environment:
    def __init__(self, config: Config) -> None:
        self.cwd = os.getcwd()
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        create_ldb.main(
            config.robot_count, config.cart_count, config.ADS_count, config.BCS_count
        )
        env_infos = LDB.fetch_env_infos()
        debug_sqlite_db.delete_from("orders_in")
        debug_sqlite_db.update_locations(config.locations)
        initialize_db(config)
        self.robot_clients = {
            name: Core("localhost:55555", f"ChargePal{number}")
            for number, name in enumerate(env_infos["robot_names"], start=1)
        }

        self.planner = Planner()

    def __enter__(self) -> "Environment":
        os.chdir(os.path.dirname(__file__))
        communication_pb2_grpc.add_CommunicationServicer_to_server(
            CommunicationServicer(self.planner), self.server
        )
        self.server.add_insecure_port("[::]:55555")
        self.server.start()
        return self

    def __exit__(
        self,
        exception_type: Type[BaseException],
        exception_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        os.chdir(self.cwd)
        self.planner.active = False

    def wait_for_job(
        self,
        client: Core,
        job_type: Optional[JobType] = None,
        timeout: float = 10.0,
    ) -> Response_Job:
        """
        With timeout, wait for client to receive its next job.
        Assert this job is of job_type, and return it.
        """
        time_start = time.time()
        while time.time() - time_start < timeout:
            response, _ = client.fetch_job()
            assert response, "No response received for grpc request."
            if response.job.job_type:
                if job_type:
                    assert (
                        response.job.job_type == job_type
                    ), f"{response.job} has wrong job type."
                logging.info(response)
                return response.job
            self.planner.tick()
            time.sleep(0.5)
        raise TimeoutError("No job.")

    def handle_events(self, events: Iterable[Event]) -> None:
        for event in events:
            logging.debug(event)
            if isinstance(event, BookingEvent):
                create_sample_booking(drop_location=event.planned_BEV_location)


def test_recharge_self() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        # Test for RECHARGE_SELF job if robot is not at RBS.
        client = environment.robot_clients["ChargePal1"]
        environment.wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")
        # Test for no job if robot is already at RBS.
        for _ in range(3):
            environment.planner.tick()
            response, _ = client.fetch_job()
            assert (
                not response.job.job_type
            ), f"Robot got job but should not have: {response.job}"


def test_bring_and_recharge() -> None:
    monitoring = Monitoring(SCENARIO2)
    with Environment(SCENARIO2.config) as environment:
        client = environment.robot_clients["ChargePal1"]
        # Book and let car appear.
        environment.handle_events(monitoring.get_next_events())
        charging_session_ids = [
            charging_session_id for charging_session_id, _ in LDB.get_session_statuses()
        ]
        # Move car to ADS_1.
        monitoring.update_car_at_ads("ADS_1")
        # Check in.
        environment.handle_events(monitoring.get_next_events())
        # Bring BAT_1 to ADS_1.
        job = environment.wait_for_job(client, JobType.BRING_CHARGER)
        assert job.target_station == "ADS_1"
        status = monitoring.get_job_status("BRING_CHARGER", job.target_station)
        assert status == "Success"
        client.update_job_monitor("BRING_CHARGER", status)
        # Recharge ChargePal1.
        environment.wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")
        # Let BAT_1 finish charging.
        LDB.update_session_status(charging_session_ids[0], BookingState.READY)
        monitoring.update_car_charged("ADS_1")
        # Bring BAT_1 to BCS_1.
        job = environment.wait_for_job(client, JobType.RECHARGE_CHARGER)
        assert job.target_station == "BCS_1"
        status = monitoring.get_job_status("RECHARGE_CHARGER", job.target_station)
        assert status == "Success"
        client.update_job_monitor("RECHARGE_CHARGER", status)

        # Handle next car.
        environment.handle_events(monitoring.get_next_events())
        environment.handle_events(monitoring.get_next_events())
        monitoring.update_car_at_ads("ADS_1", present=False)
        monitoring.update_car_at_ads("ADS_1")
        environment.handle_events(monitoring.get_next_events())
        # Bring BAT_2 to ADS_1.
        job = environment.wait_for_job(client, JobType.BRING_CHARGER)
        assert job.target_station == "ADS_1"
        status = monitoring.get_job_status("BRING_CHARGER", job.target_station)
        assert status == "Success"
        client.update_job_monitor("BRING_CHARGER", status)
        # Recharge ChargePal1.
        environment.wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")
        # Let BAT_2 finish charging.
        LDB.update_session_status(charging_session_ids[1], BookingState.READY)
        monitoring.update_car_charged("ADS_1")
        # Bring BAT_2 to BWS_1.
        job = environment.wait_for_job(client, JobType.STOW_CHARGER)
        assert job.target_station == "BWS_2", job
        status = monitoring.get_job_status("STOW_CHARGER", job.target_station)
        assert status == "Success", status
        client.update_job_monitor("STOW_CHARGER", status)

        environment.handle_events(monitoring.get_next_events())
        assert not monitoring.exists_event()
        # Recharge ChargePal1.
        environment.wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")

        # Exchange carts between waiting and charging stations.
        cart2 = environment.planner.get_cart("BAT_2")
        environment.planner.handle_charger_update(cart2, ChargerCommand.STOP_RECHARGING)
        job = environment.wait_for_job(client, JobType.STOW_CHARGER)
        assert job.target_station == "BWS_1"
        status = monitoring.get_job_status("STOW_CHARGER", job.target_station)
        assert status == "Success"
        client.update_job_monitor("STOW_CHARGER", status)
        job = environment.wait_for_job(client, JobType.RECHARGE_CHARGER)
        assert job.target_station == "BCS_1"
        status = monitoring.get_job_status("RECHARGE_CHARGER", job.target_station)
        assert status == "Success"
        client.update_job_monitor("RECHARGE_CHARGER", status)
        environment.wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")


def test_failures() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        client = environment.robot_clients["ChargePal1"]
        create_sample_booking(drop_location="ADS_1")
        charging_session_id, _ = LDB.get_session_statuses()[-1]
        job = environment.wait_for_job(client, JobType.BRING_CHARGER)
        client.update_job_monitor("BRING_CHARGER", "Failure")
        environment.planner.tick()
        assert environment.planner.get_cart(job.cart).available, job.cart
        job = environment.wait_for_job(client, JobType.BRING_CHARGER)
        client.update_job_monitor("BRING_CHARGER", "Success")
        environment.wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Failure")
        environment.wait_for_job(client, JobType.RECHARGE_SELF)
        LDB.update_session_status(charging_session_id, BookingState.READY)
        client.update_job_monitor("RECHARGE_SELF", "Failure")
        job = environment.wait_for_job(client, JobType.RECHARGE_CHARGER)
        client.update_job_monitor("RECHARGE_CHARGER", "Failure")
        environment.planner.tick()
        assert environment.planner.get_cart(job.cart).available, job.cart
        # Note: If recharging charger keeps failing after recovery,
        #  nothing more can be done for it automatically.
        environment.wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")


def test_two_twice_in_parallel() -> None:
    with Environment(CONFIG_DEFAULT) as environment:
        client1, client2 = list(environment.robot_clients.values())
        for _ in range(2):
            # Create 2 bookings, let 2 robots bring 2 carts.
            for number in (1, 2):
                create_sample_booking(drop_location=f"ADS_{number}")
            cart1 = environment.wait_for_job(client1, JobType.BRING_CHARGER).cart
            cart2 = environment.wait_for_job(client2, JobType.BRING_CHARGER).cart
            for client in environment.robot_clients.values():
                client.update_job_monitor("BRING_CHARGER", "Success")
            # Let both chargers complete while both robots recharge themselves.
            environment.wait_for_job(client1, JobType.RECHARGE_SELF)
            environment.wait_for_job(client2, JobType.RECHARGE_SELF)
            for cart in (cart1, cart2):
                environment.planner.handle_charger_update(
                    environment.planner.get_cart(cart), ChargerCommand.BOOKING_FULFILLED
                )
            for client in environment.robot_clients.values():
                client.update_job_monitor("RECHARGE_SELF", "Success")
            # Let robots retrieve the carts, remember the jobs.
            job1 = environment.wait_for_job(client1)
            job2 = environment.wait_for_job(client2)
            for job in (job1, job2):
                environment.robot_clients[job.robot_name].update_job_monitor(
                    job.job_type, "Success"
                )
            # Stop recharging the chargers which were not stowed,
            #  while both robots recharge themselves.
            environment.wait_for_job(client1, JobType.RECHARGE_SELF)
            environment.wait_for_job(client2, JobType.RECHARGE_SELF)
            for job in (job1, job2):
                assert job.job_type in (
                    "RECHARGE_CHARGER",
                    "STOW_CHARGER",
                ), job.job_type
                if job.job_type == "RECHARGE_CHARGER":
                    environment.planner.handle_charger_update(
                        environment.planner.get_cart(job.cart),
                        ChargerCommand.STOP_RECHARGING,
                    )
            for client in environment.robot_clients.values():
                client.update_job_monitor("RECHARGE_SELF", "Success")


def test_status_update() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        client = environment.robot_clients["ChargePal1"]
        create_sample_booking(
            drop_location="ADS_1", charging_session_status=BookingState.BOOKED
        )
        charging_session_id, _ = LDB.get_session_statuses()[-1]
        environment.wait_for_job(
            environment.robot_clients["ChargePal1"], JobType.RECHARGE_SELF
        )
        client.update_job_monitor("RECHARGE_SELF", "Success")
        LDB.update_session_status(charging_session_id, BookingState.CHECKED_IN)
        environment.wait_for_job(
            environment.robot_clients["ChargePal1"], JobType.BRING_CHARGER
        )


def test_plug_in_handshake() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        client = environment.robot_clients["ChargePal1"]
        create_sample_booking(drop_location="ADS_1")
        charging_session_id, _ = LDB.get_session_statuses()[-1]
        get_status = lambda: LDB.get_session_statuses()[-1][-1]
        assert get_status() == BookingState.CHECKED_IN, get_status()
        environment.wait_for_job(client, JobType.BRING_CHARGER)
        assert get_status() == BookingState.BOOKED, get_status()
        assert not environment.planner.handshake_plug_in("ChargePal1")
        assert get_status() == BookingState.PENDING, get_status()
        assert not environment.planner.handshake_plug_in("ChargePal1")
        LDB.update_session_status(charging_session_id, BookingState.PENDING)
        assert not environment.planner.handshake_plug_in("ChargePal1")
        environment.planner.tick()
        assert environment.planner.handshake_plug_in("ChargePal1")


def test_cancel_booking() -> None:
    with Environment(CONFIG_ALL_ONE) as environment:
        client = environment.robot_clients["ChargePal1"]
        create_sample_booking(drop_location="ADS_1")
        charging_session_id, _ = LDB.get_session_statuses()[-1]
        get_status = lambda: LDB.get_session_statuses()[-1][-1]
        assert get_status() == BookingState.CHECKED_IN, get_status()
        environment.planner.tick()
        LDB.update_session_status(charging_session_id, BookingState.CANCELED)
        create_sample_booking(drop_location="ADS_1")
        charging_session_id, _ = LDB.get_session_statuses()[-1]
        assert get_status() == BookingState.CHECKED_IN, get_status()
        environment.wait_for_job(client, JobType.BRING_CHARGER)
        LDB.update_session_status(charging_session_id, BookingState.CANCELED)
        create_sample_booking(drop_location="ADS_1")
        assert get_status() == BookingState.CHECKED_IN, get_status()
        environment.wait_for_job(client, JobType.BRING_CHARGER)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_recharge_self()
    test_bring_and_recharge()
    test_failures()
    test_two_twice_in_parallel()
    test_status_update()
    test_plug_in_handshake()
    test_cancel_booking()
