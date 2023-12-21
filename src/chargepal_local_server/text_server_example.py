#!/usr/bin/env python3
from typing import Any
import time
from chargepal_local_server.local_server import LocalServer
from chargepal_local_server.local_server_pb2 import EmptyMessage, PortInfo, TextMessage


class TextServer(LocalServer):
    def SendTextMessage(self, request: TextMessage, context: Any) -> EmptyMessage:
        result = super().SendTextMessage(request, context)
        print(request.text)
        return result

    def ConnectClient(self, request: PortInfo, context: Any) -> EmptyMessage:
        result = super().ConnectClient(request, context)
        print(f"Robot client connected on port {request.port}.")
        self.print_robot_ports()
        return result

    def on_inactive_rpc_error(self) -> None:
        print("Connection to robot client lost.")
        self.print_robot_ports()

    def print_robot_ports(self):
        print(f" Robot ports: [{', '.join(map(str, self.robot_client_stubs.keys()))}]")


if __name__ == "__main__":
    PING_INTERVAL = 1.0

    print(
        "Listening for messages and occassionally sending one (press <Ctrl-C> to stop) ..."
    )
    next_time = time.time() + PING_INTERVAL
    try:
        server = TextServer.serve()
        while True:
            time.sleep(next_time - time.time())
            next_time += PING_INTERVAL
            if server.robot_client_stubs:
                server.ping_robots()
    except KeyboardInterrupt:
        print()
