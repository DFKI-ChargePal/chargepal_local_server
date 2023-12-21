from typing import Any, Iterator, Optional, Type, TypeVar
from concurrent.futures import ThreadPoolExecutor
import grpc
import logging
from chargepal_local_server import local_server_pb2_grpc
from chargepal_local_server.local_server_pb2 import (
    EmptyMessage,
    Job,
    Pos,
    RobotID,
    TextMessage,
)
from chargepal_local_server.local_server_pb2_grpc import LocalServerServicer


T = TypeVar("T", bound="LocalServer")


class LocalServer(LocalServerServicer):
    IP_ADDRESS = "localhost"
    PORT = 9000

    def __init__(self, grpc_server: grpc.Server) -> None:
        super().__init__()
        self.grpc_server = grpc_server  # Note: Must be refereced for persistence.

    @classmethod
    def serve(
        cls: Type[T], ip_address: Optional[str] = None, port: Optional[int] = None
    ) -> T:
        logging.basicConfig()
        grpc_server = grpc.server(ThreadPoolExecutor(max_workers=42))
        server = cls(grpc_server)
        local_server_pb2_grpc.add_LocalServerServicer_to_server(server, grpc_server)
        grpc_server.add_insecure_port(
            f"{ip_address if ip_address else cls.IP_ADDRESS}:{port if port else cls.PORT}"
        )
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

    def FetchJob(self, request: RobotID, context: Any) -> Job:
        return Job(
            job_type="BRING_CHARGER",
            charger="BAT_1",
            source_station="ADS_1",
            target_station="ADS_2",
        )
