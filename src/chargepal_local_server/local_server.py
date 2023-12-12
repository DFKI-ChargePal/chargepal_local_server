from typing import Deque, Dict, Optional, Type
from types import TracebackType
from collections import deque
from multiprocessing.connection import Client, Connection, Listener
from threading import Condition, Thread


class LocalServer:
    SERVER_ADDRESS = ("localhost", 1024)

    def __init__(self) -> None:
        self.active = True
        self.messages: Deque[str] = deque()
        self.condition = Condition()
        self.robot_connections: Dict[int, Connection] = {}
        self.listener = Listener(self.SERVER_ADDRESS)
        self.listener_thread = Thread(target=self.listen)
        self.listener_thread.start()

    def __enter__(self) -> "LocalServer":
        return self

    def __exit__(
        self,
        exception_type: Type[BaseException],
        exception_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        self.shutdown()

    def listen(self) -> None:
        """
        Listen for messages from all robots on a single port.
         Therefore, reestablish connection after each message
         because different senders might be sending at any time.
         Synchronize the incoming messages into a message queue.
        """
        while self.active:
            connection = self.listener.accept()
            try:
                message = str(connection.recv())
                self.condition.acquire()
                self.messages.append(message)
                self.condition.notify_all()
                self.condition.release()
            except EOFError:
                pass
            finally:
                connection.close()

    def connect(self, port: int) -> None:
        """Connect to robot client and store connection."""
        self.robot_connections[port] = Client((self.SERVER_ADDRESS[0], port))

    def send(self, port: int, message: str) -> None:
        """Send message to robot at port."""
        try:
            self.robot_connections[port].send(message)
        except BrokenPipeError as e:
            del self.robot_connections[port]
            raise e

    def wait_for_message(self, timeout: Optional[float] = None) -> Optional[str]:
        """Wait for message or until a timeout occurs."""
        self.condition.acquire()
        self.condition.wait(timeout)
        message = self.messages.popleft() if self.messages else None
        self.condition.release()
        return message

    def shutdown(self) -> None:
        if self.active:
            self.active = False
            Client(self.SERVER_ADDRESS).close()
            for connection in self.robot_connections.values():
                connection.close()
            self.listener.close()
            self.listener_thread.join()
