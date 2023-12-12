#!/usr/bin/env python3
import time
from chargepal_local_server.local_server import LocalServer


class TestServer(LocalServer):
    def print_robot_connections(self) -> None:
        print(f" Robot ports: [{', '.join(map(str, self.robot_connections.keys()))}]")


if __name__ == "__main__":
    PING_INTERVAL = 1.0

    print(
        "Listening for messages and occassionally sending one (press <Ctrl-C> to stop) ..."
    )
    server = TestServer()
    connection_index = 0
    next_time = time.time() + PING_INTERVAL
    while server.active:
        try:
            if server.messages:
                message = server.messages.pop(0)
                print(message)

                tokens = message.split()
                if tokens[0] == "REQUEST_PORT":
                    server.connect(int(tokens[1]))
                    server.print_robot_connections()
            if time.time() >= next_time:
                if server.robot_connections:
                    connection_index += 1
                    if connection_index >= len(server.robot_connections):
                        connection_index = 0
                    try:
                        server.send(
                            list(server.robot_connections.keys())[connection_index],
                            "PING",
                        )
                    except BrokenPipeError as e:
                        print(e)
                        server.print_robot_connections()
                next_time += PING_INTERVAL
            time.sleep(0.1)
        except KeyboardInterrupt:
            server.shutdown()
