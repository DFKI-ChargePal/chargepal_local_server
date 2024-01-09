#!/usr/bin/env python3
import grpc
import communication_pb2
import communication_pb2_grpc
from concurrent import futures
import threading
import queue
import time
import job
import free_station
import update_ldb

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class CommunicationServicer(communication_pb2_grpc.CommunicationServicer):
    def __init__(self):

        self.request_lock = threading.Lock()
        self.job_success_status = True

    def process_request(self, request):
        with self.request_lock:

            if request.request_name == "fetch_job":
                self.job_success_status = False
                job_details = job.fetch_job(request.robot_name)
                time.sleep(5)
                response = communication_pb2.Response_FetchJob(
                    message="finished processing",
                    job=communication_pb2.Response_Job(**job_details),
                )

            elif request.request_name == "ask_free_bcs":
                available_station = free_station.search_bcs(request.robot_name)
                response = communication_pb2.Response_FreeStation(
                    station_name=available_station
                )

            elif request.request_name == "ask_free_bws":
                available_station = free_station.search_bws(request.robot_name)
                response = communication_pb2.Response_FreeStation(
                    station_name=available_station
                )

            elif request.request_name == "reset_bcs_blocker":
                status = free_station.reset_bcs_blocker(request.robot_name)
                response = communication_pb2.Response_ResetStationBlocker(
                    success=status
                )

            elif request.request_name == "reset_bws_blocker":
                status = free_station.reset_bws_blocker(request.robot_name)
                response = communication_pb2.Response_ResetStationBlocker(
                    success=status
                )

            elif request.request_name == "push_to_ldb":
                status = update_ldb.update(request.table_name, request.rdb_data)
                response = communication_pb2.Response_PushToLDB(success=status)

            elif request.request_name == "update_job_monitor":
                self.job_success_status = True  # ToDo: update job monitor
                response = communication_pb2.Response_UpdateJobMonitor(
                    success=self.job_success_status
                )

            elif request.request_name == "operation_time":
                requested_cart = request.cart_name
                status = True  # ToDo: Calculate the time left for the cart to finish charging job
                response = communication_pb2.Response_UpdateJobMonitor(msec=30000)

        return response

    def UpdateRDB(self, request, context):
        robot_name = request.robot_name
        with open("db/ldb.db", "rb") as file:
            file_content = file.read()

        return communication_pb2.Response_UpdateRDB(ldb=file_content)

    def FetchJob(self, request, context):
        request_data = request
        response = self.process_request(request_data)

        return response

    def AskFreeStation(self, request, context):
        request_data = request
        response = self.process_request(request_data)

        return response

    def PushToLDB(self, request, context):
        request_data = request
        response = self.process_request(request_data)
        return response

    def ResetStationBlocker(self, request, context):
        request_data = request
        response = self.process_request(request_data)
        return response

    def UpdateJobMonitor(self, request, context):
        request_data = request
        response = self.process_request(request_data)
        return response

    def OperationTime(self, request, context):
        request_data = request
        response = self.process_request(request_data)
        return response


def server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    communication_pb2_grpc.add_CommunicationServicer_to_server(
        CommunicationServicer(), server
    )
    server.add_insecure_port("[::]:50059")
    server.start()

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    server_thread = threading.Thread(target=server)
    server_thread.start()
    server_thread.join()
