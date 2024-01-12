#!/usr/bin/env python3
from typing import Any
import grpc
import communication_pb2
import communication_pb2_grpc
from concurrent import futures
import threading
import time
import job
import free_station
import update_ldb
from communication_pb2 import (
    Request,
    Response_FetchJob,
    Response_FreeStation,
    Response_PushToLDB,
    Response_ResetStationBlocker,
    Response_UpdateJobMonitor,
    Response_UpdateRDB,
)


class CommunicationServicer(communication_pb2_grpc.CommunicationServicer):
    def __init__(self):
        self.request_lock = threading.Lock()
        self.job_success_status = True

    def UpdateRDB(self, request: Request, context: Any) -> Response_UpdateRDB:
        robot_name = request.robot_name
        with open("db/ldb.db", "rb") as file:
            file_content = file.read()

        return communication_pb2.Response_UpdateRDB(ldb=file_content)

    def FetchJob(self, request: Request, context: Any) -> Response_FetchJob:
        with self.request_lock:
            self.job_success_status = False
            job_details = job.fetch_job(request.robot_name)
            time.sleep(5)
            response = communication_pb2.Response_FetchJob(
                message="finished processing",
                job=communication_pb2.Response_Job(**job_details),
            )
        return response

    def AskFreeStation(self, request: Request, context: Any) -> Response_FreeStation:
        with self.request_lock:
            if request.request_name == "ask_free_bcs":
                available_station = free_station.search_free_station(
                    request.robot_name, "BCS_"
                )
                response = communication_pb2.Response_FreeStation(
                    station_name=available_station
                )
            elif request.request_name == "ask_free_bws":
                available_station = free_station.search_free_station(
                    request.robot_name, "BWS_"
                )
                response = communication_pb2.Response_FreeStation(
                    station_name=available_station
                )
        assert response, f"Invalid request name: '{request.request_name}'"
        return response

    def PushToLDB(self, request: Request, context: Any) -> Response_PushToLDB:
        with self.request_lock:
            status = update_ldb.update(request.table_name, request.rdb_data)
            response = communication_pb2.Response_PushToLDB(success=status)
        return response

    def ResetStationBlocker(
        self, request: Request, context: Any
    ) -> Response_ResetStationBlocker:
        with self.request_lock:
            if request.request_name == "reset_bcs_blocker":
                status = free_station.reset_blockers(request.robot_name, "BCS_")
                response = communication_pb2.Response_ResetStationBlocker(
                    success=status
                )
            elif request.request_name == "reset_bws_blocker":
                status = free_station.reset_blockers(request.robot_name, "BWS_")
                response = communication_pb2.Response_ResetStationBlocker(
                    success=status
                )
        assert response, f"Invalid request name: '{request.request_name}'"
        return response

    def UpdateJobMonitor(
        self, request: Request, context: Any
    ) -> Response_UpdateJobMonitor:
        with self.request_lock:
            self.job_success_status = True  # ToDo: update job monitor
            response = communication_pb2.Response_UpdateJobMonitor(
                success=self.job_success_status
            )
        return response

    def OperationTime(
        self, request: Request, context: Any
    ) -> Response_UpdateJobMonitor:
        with self.request_lock:
            requested_cart = request.cart_name
            status = True  # ToDo: Calculate the time left for the cart to finish charging job
            response = communication_pb2.Response_UpdateJobMonitor(msec=30000)
        return response


def server() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    communication_pb2_grpc.add_CommunicationServicer_to_server(
        CommunicationServicer(), server
    )
    server.add_insecure_port("[::]:50059")
    server.start()
    stop_event = threading.Event()
    try:
        stop_event.wait()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    server()
