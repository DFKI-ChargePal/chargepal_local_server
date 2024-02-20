"""
Test script to test planner on custom scenarios.

The tests use scripts of local server and robot clients with grpc
communication without ROS.
Execution and message polling is accelerated a lot, so the tests
are not suited as real-time tests.
"""

#!/usr/bin/env python3
from typing import Optional, Type
from types import TracebackType
from concurrent import futures
from dataclasses import dataclass
from threading import Thread
from communication_pb2 import Response_Job
import communication_pb2_grpc
import grpc
import os
import time
import debug_ldb
from create_ldb_orders import create_sample_booking
from planner import ChargerCommand, JobType, Planner
from server import CommunicationServicer
from chargepal_client.core import Core


# Note: Reconnect on file level for pytest.
ldb_filepath = debug_ldb.get_db_filepath(__file__, "test_ldb.db")
debug_ldb.connect(ldb_filepath)


@dataclass
class Env:
    counts: str
    locations: str


ENV_ALL_ONE = Env(
    "robots: 1, carts: 1, RBS: 1, ADS: 1, BCS: 1, BWS: 1",
    {
        "ChargePal1": "RBS_1",
        "BAT_1": "BWS_1",
    },
)
ENV_DEFAULT = Env(
    "robots: 2, carts: 3, RBS: 2, ADS: 2, BCS: 2, BWS: 3",
    {
        "ChargePal1": "RBS_1",
        "ChargePal2": "RBS_2",
        "BAT_1": "BWS_1",
        "BAT_2": "BWS_2",
        "BAT_3": "BWS_3",
    },
)


class Scenario:
    def __init__(self, env: Env) -> None:
        self.cwd = os.getcwd()
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        debug_ldb.counts.set(env.counts)
        debug_ldb.delete_from("orders_in")
        # Set all locations to none for entities unused
        #  to prevent them from blocking stations erroneously.
        debug_ldb.update("robot_info SET robot_location = 'NONE'")
        debug_ldb.update("cart_info SET cart_location = 'NONE'")
        debug_ldb.update_locations(env.locations)
        self.robot_clients = {
            f"ChargePal{number}": Core("localhost:55555", f"ChargePal{number}")
            for number in range(1, debug_ldb.counts.robots + 1)
        }
        self.planner: Planner
        self.thread: Thread

    def __enter__(self) -> "Scenario":
        os.chdir(os.path.dirname(__file__))
        self.planner = Planner(ldb_filepath)
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
                if response.job.job_type:
                    print(response)
                    return response.job
            if time.time() - time_start >= timeout:
                raise TimeoutError("No job.")


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
    if job_type and response.job.job_type != job_type.name:
        raise RuntimeError("Wrong job type.")
    return response.job


def test_recharge_self() -> None:
    with Scenario(ENV_ALL_ONE) as scenario:
        wait_for_job(scenario.robot_clients["ChargePal1"], JobType.RECHARGE_SELF)


def test_bring_and_recharge() -> None:
    with Scenario(ENV_ALL_ONE) as scenario:
        client = scenario.robot_clients["ChargePal1"]
        create_sample_booking(ldb_filepath, drop_location="ADS_1")
        wait_for_job(client, JobType.BRING_CHARGER)
        client.update_job_monitor("BRING_CHARGER", "Success")
        wait_for_job(client, JobType.RECHARGE_SELF)
        scenario.planner.handle_charger_update("BAT_1", ChargerCommand.RETRIEVE_CHARGER)
        client.update_job_monitor("RECHARGE_SELF", "Success")
        wait_for_job(client, JobType.RECHARGE_CHARGER)
        client.update_job_monitor("RECHARGE_CHARGER", "Success")
        wait_for_job(client, JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")


def test_two_twice_in_parallel() -> None:
    with Scenario(ENV_DEFAULT) as scenario:
        for _ in range(2):
            # Create 2 bookings, let 2 robots bring 2 carts.
            for number in (1, 2):
                create_sample_booking(ldb_filepath, drop_location=f"ADS_{number}")
            cart1 = scenario.wait_for_next_job().cart
            cart2 = scenario.wait_for_next_job().cart
            for client in scenario.robot_clients.values():
                client.update_job_monitor("BRING_CHARGER", "Success")
            # Let both chargers complete while both robots recharge themselves.
            for _ in range(2):
                scenario.wait_for_next_job()
            for charger in (cart1, cart2):
                scenario.planner.handle_charger_update(
                    charger, ChargerCommand.BOOKING_FULFILLED
                )
            for client in scenario.robot_clients.values():
                client.update_job_monitor("RECHARGE_SELF", "Success")
            # Let robots retrieve the carts, remember the jobs.
            job1 = scenario.wait_for_next_job()
            job2 = scenario.wait_for_next_job()
            for job in (job1, job2):
                scenario.robot_clients[job.robot_name].update_job_monitor(
                    job.job_type, "Success"
                )
            # Stop recharging the chargers which were not stowed,
            #  while both robots recharge themselves.
            for _ in range(2):
                scenario.wait_for_next_job()
            for job in (job1, job2):
                assert job.job_type in (
                    "RECHARGE_CHARGER",
                    "STOW_CHARGER",
                ), job.job_type
                if job.job_type == "RECHARGE_CHARGER":
                    scenario.planner.handle_charger_update(
                        job.cart, ChargerCommand.STOP_RECHARGING
                    )
            for client in scenario.robot_clients.values():
                client.update_job_monitor("RECHARGE_SELF", "Success")


def test_status_update() -> None:
    with Scenario(ENV_ALL_ONE) as scenario:
        client = scenario.robot_clients["ChargePal1"]
        create_sample_booking(
            ldb_filepath, drop_location="ADS_1", charging_session_status="booked"
        )
        wait_for_job(scenario.robot_clients["ChargePal1"], JobType.RECHARGE_SELF)
        client.update_job_monitor("RECHARGE_SELF", "Success")
        debug_ldb.update("orders_in SET charging_session_status = 'checked_in'")
        wait_for_job(scenario.robot_clients["ChargePal1"], JobType.BRING_CHARGER)


def test_plug_in_handshake() -> None:
    with Scenario(ENV_ALL_ONE) as scenario:
        client = scenario.robot_clients["ChargePal1"]
        create_sample_booking(ldb_filepath, drop_location="ADS_1")
        wait_for_job(client, JobType.BRING_CHARGER)
        get_status = lambda: debug_ldb.select(
            "charging_session_status FROM orders_in",
        )[-1][0]
        assert get_status() == "checked_in", get_status()
        assert not scenario.planner.robot_ready2plug("ChargePal1")
        assert get_status() == "robot_ready2plug", get_status()
        assert not scenario.planner.robot_ready2plug("ChargePal1")
        debug_ldb.update(
            "orders_in SET charging_session_status == 'BEV_pending'"
            " WHERE charging_session_status == 'robot_ready2plug'"
        )
        assert not scenario.planner.robot_ready2plug("ChargePal1")
        scenario.planner.handle_updated_bookings()
        assert scenario.planner.robot_ready2plug("ChargePal1")


if __name__ == "__main__":
    test_recharge_self()
    test_bring_and_recharge()
    test_two_twice_in_parallel()
    test_status_update()
    test_plug_in_handshake()
