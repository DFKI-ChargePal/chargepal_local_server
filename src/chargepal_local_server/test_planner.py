from typing import Optional, Type
from types import TracebackType
from concurrent import futures
from threading import Thread
import communication_pb2_grpc
import grpc
import os
import time
import debug_ldb
from create_ldb_orders import create_sample_booking
from planner import Planner
from server import CommunicationServicer
from chargepal_client.core import Core


ldb_filepath = debug_ldb.get_db_filepath(__file__, "test_ldb.db")
# Note: Reconnect on file level for pytest.
debug_ldb.connect(ldb_filepath)


class Scenario:
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = path if path else os.path.dirname(__file__)
        self.original_path = os.getcwd()
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        self.robot_client = Core("localhost:55555", "ChargePal1")
        self.planner: Planner
        self.thread: Thread

    def __enter__(self) -> "Scenario":
        os.chdir(self.path)
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
        os.chdir(self.original_path)
        self.planner.active = False


def wait_for_job(scenario: Scenario, job_type: str, timeout: float = 1.0) -> None:
    time_start = time.time()
    while True:
        response, _ = scenario.robot_client.fetch_job()
        if response.job.job_type:
            break
        if time.time() - time_start >= timeout:
            raise TimeoutError("No job.")
    print(response)
    if response.job.job_type != job_type:
        raise RuntimeError("Wrong job type.")


def test_recharge_self() -> None:
    with Scenario() as scenario:
        wait_for_job(scenario, "RECHARGE_SELF")


def test_bring_charger() -> None:
    debug_ldb.delete_table("orders_in")
    with Scenario() as scenario:
        create_sample_booking(ldb_filepath)
        wait_for_job(scenario, "BRING_CHARGER")


if __name__ == "__main__":
    test_recharge_self()
    test_bring_charger()
