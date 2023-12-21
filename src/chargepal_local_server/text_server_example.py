#!/usr/bin/env python3
from typing import Any
from chargepal_local_server.local_server import LocalServer
from chargepal_local_server.local_server_pb2 import EmptyMessage, TextMessage


class TextServer(LocalServer):
    def SendTextMessage(self, request: TextMessage, context: Any) -> EmptyMessage:
        result = super().SendTextMessage(request, context)
        print(request.text)
        return result


if __name__ == "__main__":
    print("Listening for messages (press <Ctrl-C> to stop) ...")
    try:
        server = TextServer.serve()
        server.grpc_server.wait_for_termination()
    except KeyboardInterrupt:
        print()
