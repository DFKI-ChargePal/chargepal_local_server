"""
Test script to test planner on custom scenarios.

The tests use scripts of local server and robot clients with grpc
communication without ROS.
Execution and message polling is accelerated a lot, so the tests
are not suited as real-time tests.
"""

#!/usr/bin/env python3
from typing import Dict, Optional, Type
from types import TracebackType
from concurrent import futures
from threading import Thread
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


class Scenario:
    ENV_ALL_ONE = "robots: 1, carts: 1, RBS: 1, ADS: 1, BCS: 1, BWS: 1"

    def __init__(
        self,
        working_directory: Optional[str] = None,
        env_info_counts: Optional[str] = None,
    ) -> None:
        self.working_directory = (
            working_directory if working_directory else os.path.dirname(__file__)
        )
        self.original_working_directory = os.getcwd()
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        if env_info_counts:
            debug_ldb.counts.set(env_info_counts)
        self.robot_clients = {
            f"ChargePal{number}": Core("localhost:55555", f"ChargePal{number}")
            for number in range(1, debug_ldb.counts.robots + 1)
        }
        self.planner: Planner
        self.thread: Thread

    def __enter__(self) -> "Scenario":
        os.chdir(self.working_directory)
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
        os.chdir(self.original_working_directory)
        self.planner.active = False


def wait_for_job(client: Core, job_type: JobType, timeout: float = 1.0) -> None:
    time_start = time.time()
    while True:
        response, _ = client.fetch_job()
        if response.job.job_type:
            break
        if time.time() - time_start >= timeout:
            raise TimeoutError("No job.")
    print(response)
    if response.job.job_type != job_type.name:
        raise RuntimeError("Wrong job type.")


def test_recharge_self() -> None:
    with Scenario(env_info_counts=Scenario.ENV_ALL_ONE) as scenario:
        wait_for_job(scenario.robot_clients["ChargePal1"], JobType.RECHARGE_SELF)


def test_bring_and_recharge() -> None:
    debug_ldb.delete_from("orders_in")
    with Scenario(env_info_counts=Scenario.ENV_ALL_ONE) as scenario:
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


if __name__ == "__main__":
    test_recharge_self()
    test_bring_and_recharge()
