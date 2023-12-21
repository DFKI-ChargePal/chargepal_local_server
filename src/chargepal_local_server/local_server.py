from typing import Any, Iterator, Type, TypeVar
from concurrent.futures import ThreadPoolExecutor
import grpc
import logging
from chargepal_local_server import local_server_pb2_grpc
from chargepal_local_server.local_server_pb2 import EmptyMessage, Pos, TextMessage
from chargepal_local_server.local_server_pb2_grpc import LocalServerServicer


T = TypeVar("T", bound="LocalServer")


class LocalServer(LocalServerServicer):
    IP_ADDRESS = "192.168.158.25"
    PORT = 9000

    def __init__(self, grpc_server: grpc.Server) -> None:
        super().__init__()
        self.grpc_server = grpc_server  # Note: Must be refereced for persistence.

    @classmethod
    def serve(cls: Type[T]) -> T:
        logging.basicConfig()
        grpc_server = grpc.server(ThreadPoolExecutor(max_workers=42))
        server = cls(grpc_server)
        local_server_pb2_grpc.add_LocalServerServicer_to_server(server, grpc_server)
        grpc_server.add_insecure_port(f"{cls.IP_ADDRESS}:{cls.PORT}")
        grpc_server.start()
        return server

    def Ping(self, request: EmptyMessage, context: Any) -> EmptyMessage:
        """Ping between robot client and local server."""
        return EmptyMessage()

    def SendTextMessage(self, request: TextMessage, context: Any) -> EmptyMessage:
        """Receive a text message from the client."""
        return EmptyMessage()

    def UpdatePos(self, request: Pos, context: Any) -> Iterator[Pos]:
        """
        Let robot client update its position and get position updates
        for the other robots from the server.
        """
