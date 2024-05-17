#!/usr/bin/env python3
from typing import Any
from concurrent import futures
from chargepal_local_server import communication_pb2_grpc
from chargepal_local_server import free_station
from chargepal_local_server import battery_communication
import grpc
import threading
from chargepal_local_server import update_ldb
from chargepal_local_server import read_serialize_ldb
from chargepal_local_server.communication_pb2 import (
    Request,
    Response_FetchJob,
    Response_FreeStation,
    Response_Job,
    Response_PushToLDB,
    Response_Ready2PlugInADS,
    Response_ResetStationBlocker,
    Response_UpdateJobMonitor,
    Response_UpdateRDB,
    Response_PullLDB,
    Response_BatteryCommunication,
    Response_OperationTime,
)
from chargepal_local_server.planner import Planner


class CommunicationServicer(communication_pb2_grpc.CommunicationServicer):
    def __init__(self, planner: Planner):
        self.planner = planner
        self.request_lock = threading.Lock()
        self.job_success_status = True

    def UpdateRDB(self, request: Request, context: Any) -> Response_UpdateRDB:
        response = read_serialize_ldb.read_serialize()
        return response

    def PullLDB(self, request: Request, context: Any) -> Response_PullLDB:
        with open("db/ldb.db", "rb") as file:
            file_content = file.read()
        return Response_PullLDB(ldb=file_content)

    def FetchJob(self, request: Request, context: Any) -> Response_FetchJob:
        with self.request_lock:
            self.job_success_status = False
            job_details = self.planner.fetch_job(request.robot_name)
            response = Response_FetchJob(
                message="finished processing",
                job=Response_Job(**job_details),
            )
        return response

    def AskFreeStation(self, request: Request, context: Any) -> Response_FreeStation:
        with self.request_lock:
            if request.request_name == "ask_free_bcs":
                available_station = free_station.search_free_station(
                    request.robot_name, "BCS_"
                )
                response = Response_FreeStation(station_name=available_station)
            elif request.request_name == "ask_free_bws":
                available_station = free_station.search_free_station(
                    request.robot_name, "BWS_"
                )
                response = Response_FreeStation(station_name=available_station)
        assert response, f"Invalid request name: '{request.request_name}'"
        return response

    def PushToLDB(self, request: Request, context: Any) -> Response_PushToLDB:
        with self.request_lock:
            status = update_ldb.update(request.table_name, request.rdb_data)
            response = Response_PushToLDB(success=status)
        return response

    def ResetStationBlocker(
        self, request: Request, context: Any
    ) -> Response_ResetStationBlocker:
        with self.request_lock:
            if request.request_name == "reset_bcs_blocker":
                status = free_station.reset_blockers(request.robot_name, "BCS_")
                response = Response_ResetStationBlocker(success=status)
            elif request.request_name == "reset_bws_blocker":
                status = free_station.reset_blockers(request.robot_name, "BWS_")
                response = Response_ResetStationBlocker(success=status)
        assert response, f"Invalid request name: '{request.request_name}'"
        return response

    def UpdateJobMonitor(
        self, request: Request, context: Any
    ) -> Response_UpdateJobMonitor:
        with self.request_lock:
            self.job_success_status = self.planner.update_job(
                request.robot_name, request.job_name, request.job_status
            )
            response = Response_UpdateJobMonitor(success=self.job_success_status)
        return response

    def OperationTime(
        self, request: Request, context: Any
    ) -> Response_OperationTime:
        with self.request_lock:
            requested_cart = request.cart_name
            status = True  # ToDo: Calculate the time left for the cart to finish charging job
            response = Response_OperationTime(msec=30000)
        return response

    def Ready2PlugInADS(
        self, request: Request, context: Any
    ) -> Response_Ready2PlugInADS:
        with self.request_lock:
            ready_to_plugin = self.planner.handshake_plug_in(request.robot_name)
            response = Response_Ready2PlugInADS(ready_to_plugin)
        return response
    def BatteryCommunication(self, request: Request, context: Any
    ) -> Response_BatteryCommunication:
        with self.request_lock:
            request_name = request.request_name
            success = False
            cart_name = request.cart_name
            
            if request_name == "wakeup":
                success = battery_communication.wakeup(cart_name)
            elif request_name == "mode_req_standby":
                success = battery_communication.mode_req_standby(cart_name)
            elif request_name == "mode_req_idle":
                success = battery_communication.mode_req_idle(cart_name)
            elif request_name == "mode_req_EV_AC_Charge":
                success = battery_communication.mode_req_EV_AC_Charge(cart_name)
            elif request_name == "mode_req_EV_DC_Charge":
                success = battery_communication.mode_req_EV_DC_Charge(cart_name)
            elif request_name == "mode_req_Bat_AC_Charge":
                success = battery_communication.mode_req_Bat_AC_Charge(cart_name)
            elif request_name == "ladeprozess_start":
                success = battery_communication.ladeprozess_start(cart_name)
            elif request_name == "ladeprozess_end":
                success = battery_communication.ladeprozess_end(cart_name)
            
            response = Response_BatteryCommunication(success=success)
            return response

def server() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    planner = Planner()
    communication_pb2_grpc.add_CommunicationServicer_to_server(
        CommunicationServicer(planner), server
    )
    server.add_insecure_port("[::]:50059")
    server.start()
    try:
        planner.run()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    server()
