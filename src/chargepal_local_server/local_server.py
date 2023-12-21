from typing import Any, Dict, Iterator, Type, TypeVar
from concurrent.futures import ThreadPoolExecutor
from grpc._channel import _InactiveRpcError
import grpc
import logging
from chargepal_local_server import local_server_pb2_grpc
from chargepal_local_server.local_server_pb2 import (
    EmptyMessage,
    PortInfo,
    Pos,
    TextMessage,
)
from chargepal_local_server.local_server_pb2_grpc import (
    LocalServerServicer,
    RobotClientStub,
)


T = TypeVar("T", bound="LocalServer")


class LocalServer(LocalServerServicer):
    IP_ADDRESS = "192.168.158.25"
    PORT = 9000

    def __init__(self, grpc_server: grpc.Server) -> None:
        super().__init__()
        self.grpc_server = grpc_server  # Note: Must be refereced for persistence.
        self.robot_client_stubs: Dict[int, RobotClientStub] = {}

    @classmethod
    def serve(cls: Type[T]) -> T:
        logging.basicConfig()
        grpc_server = grpc.server(ThreadPoolExecutor(max_workers=42))
        server = cls(grpc_server)
        local_server_pb2_grpc.add_LocalServerServicer_to_server(server, grpc_server)
        grpc_server.add_insecure_port(f"{cls.IP_ADDRESS}:{cls.PORT}")
        grpc_server.start()
        return server

    def ConnectClient(self, request: PortInfo, context: Any) -> EmptyMessage:
        """Connect to robot client on the port provided."""
        channel = grpc.insecure_channel(f"{self.IP_ADDRESS}:{request.port}")
        self.robot_client_stubs[request.port] = RobotClientStub(channel)
        return EmptyMessage()

    def SendTextMessage(self, request: TextMessage, context: Any) -> EmptyMessage:
        """Receive a text message from the client."""
        return EmptyMessage()

    def UpdatePos(self, request: Pos, context: Any) -> Iterator[Pos]:
        """
        Let robot client update its position and get position updates
        for the other robots from the server.
        """

    def ping_robots(self) -> None:
        try:
            for port, stub in self.robot_client_stubs.items():
                stub.Ping(EmptyMessage())
        except _InactiveRpcError:
            del self.robot_client_stubs[port]
            self.on_inactive_rpc_error()

    def on_inactive_rpc_error(self) -> None:
        pass
