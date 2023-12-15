from typing import Callable, Deque, Dict, Optional, Tuple, Type
from types import TracebackType
from collections import deque
from multiprocessing.connection import Client, Connection, Listener
from threading import Condition, Thread
import re


class LocalServer:
    SERVER_ADDRESS = ("192.168.158.25", 9000)

    def __init__(self) -> None:
        self.active = True
        self._messages: Deque[str] = deque()
        self._message_handlers: Dict[str, Callable[[Tuple[str]], object]] = {}
        self._condition = Condition()
        self.robot_connections: Dict[int, Connection] = {}
        self._listener = Listener(self.SERVER_ADDRESS)
        self._listener_thread = Thread(target=self.listen)
        self._listener_thread.start()

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
            connection = self._listener.accept()
            try:
                message = str(connection.recv())
                self._condition.acquire()
                self._messages.append(message)
                self._condition.notify_all()
                self._condition.release()
            except EOFError:
                pass
            finally:
                connection.close()

    def connect(self, port: int) -> None:
        """Connect to robot client and store connection."""
        try:
            # Note: Using with Jetson Orin IP address in Agro-Technicum for now.
            self.robot_connections[port] = Client(("192.168.158.33", port))
        except ConnectionRefusedError as e:
            raise e

    def send(self, port: int, message: str) -> None:
        """Send message to robot at port."""
        try:
            self.robot_connections[port].send(message)
        except (BrokenPipeError, ConnectionResetError) as e:
            del self.robot_connections[port]
            raise e

    def wait_for_message(self, timeout: Optional[float] = None) -> Optional[str]:
        """Wait for message or until a timeout occurs."""
        self._condition.acquire()
        self._condition.wait(timeout)
        message = self._messages.popleft() if self._messages else None
        self._condition.release()
        return message

    def add_message_handler(
        self, pattern: str, handler: Callable[[Tuple[str]], object]
    ) -> None:
        self._message_handlers[pattern] = handler

    def add_message_handlers(
        self, message_handlers: Dict[str, Callable[[Tuple[str]], object]]
    ) -> None:
        for pattern, handler in message_handlers.items():
            self.add_message_handler(pattern, handler)

    def handle_message(self, message: str) -> None:
        for pattern, handler in self._message_handlers.items():
            match_result = re.match(pattern, message)
            if match_result:
                handler(match_result.groups())

    def shutdown(self) -> None:
        if self.active:
            self.active = False
            Client(self.SERVER_ADDRESS).close()
            for connection in self.robot_connections.values():
                connection.close()
            self._listener.close()
            self._listener_thread.join()
