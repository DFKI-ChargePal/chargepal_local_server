#!/usr/bin/env python3
"""
Simple grid-based simulation with str presentations.

It connects with robots and maintains their representations
 over connection losses.
"""

from typing import Dict, List, Optional
from enum import Enum
import re
import time
from chargepal_local_server.local_server import LocalServer


class TileType(Enum):
    BORDER = "X"
    WALL = "X"
    FREE = " "
    GOAL = "*"


class Tile:
    def __init__(self, x: int, y: int, tile_type: TileType) -> None:
        self.x, self.y = x, y
        self.type = tile_type
        self._mobile: Optional[Mobile] = None

    def __str__(self) -> str:
        return str(self.mobile) if self.mobile else self.type.value

    @property
    def mobile(self) -> Optional["Mobile"]:
        return self._mobile

    @mobile.setter
    def mobile(self, value: Optional["Mobile"]):
        assert (self._mobile is None) != (value is None)
        self._mobile = value

    def is_free(self) -> bool:
        return self.type == TileType.FREE and not self._mobile


class Area:
    def __init__(self, name: str, width: int, height: int) -> None:
        self.name = name
        self.width = width
        self.height = height
        self.outer_width = width + 2
        self.outer_height = height + 2
        self.tiles = [
            [
                Tile(
                    x,
                    y,
                    TileType.FREE if self.is_inside(x, y) else TileType.BORDER,
                )
                for y in range(self.outer_height)
            ]
            for x in range(self.outer_width)
        ]

    def __str__(self) -> str:
        return "\n".join(
            "".join(str(self.tiles[x][y]) for x in range(self.outer_width))
            for y in range(self.outer_height)
        )

    def is_inside(self, x: int, y: int) -> bool:
        return 0 < x <= self.width and 0 < y <= self.height


class Mobile:
    def __init__(self, area: Area, x: int, y: int) -> None:
        self.area = area
        self.x, self.y = x, y
        self.area.tiles[x][y].mobile = self

    def __str__(self) -> str:
        return "?"

    def get_tile(self, dx: int, dy: int) -> Tile:
        return self.area.tiles[self.x + dx][self.y + dy]

    def move_to(self, x: int, y: int) -> None:
        self.area.tiles[self.x][self.y].mobile = None
        self.x, self.y = x, y
        self.area.tiles[self.x][self.y].mobile = self

    def move(self, dx: int, dy: int) -> None:
        self.move_to(self.x + dx, self.y + dy)


class Robot(Mobile):
    def __init__(self, area: Area, x: int, y: int) -> None:
        super().__init__(area, x, y)
        self.is_connected = True

    def __str__(self) -> str:
        return f"\033[9{7 if self.is_connected else 1}mR\033[m"


class Sim(LocalServer):
    TICK_INTERVAL = 1.0

    def __init__(self) -> None:
        super().__init__()
        self.area = Area("Area01", 8, 3)
        self.robots: Dict[int, Robot] = {}
        self.tick_count = 0
        self.print_area()
        self.next_time = time.time() + self.TICK_INTERVAL

    def print_area(self) -> None:
        print(str(self.area), self.tick_count)

    def match_into_tokens(self, pattern: str, string: str, tokens: List[str]) -> bool:
        """
        Try to match string against pattern and return whether successful.
         Replace tokens by match results.
        """
        tokens.clear()
        if not pattern.endswith("$"):
            pattern += "$"
        match_result = re.match(pattern, string)
        if match_result:
            tokens.extend(match_result.groups())
            return True
        return False

    def handle_message(self, message: str) -> None:
        tokens: List[str] = []
        if self.match_into_tokens(r"REQUEST_PORT (\d+)", message, tokens):
            port = int(tokens[0])
            # Connect with robot on port.
            self.connect(port)
            if port in self.robots.keys():
                self.robots[port].is_connected = True
            else:
                self.robots[port] = Robot(self.area, len(self.robots) + 1, 1)
        elif self.match_into_tokens(r"(\d+) POS (\d+) (\d+)", message, tokens):
            robot_id, x, y = list(map(int, tokens))
            # Update robot_id's (x, y) position.
            if (
                robot_id in self.robots.keys()
                and self.area.is_inside(x, y)
                and self.area.tiles[x][y].is_free()
            ):
                robot = self.robots[robot_id]
                if robot.is_connected:
                    self.robots[robot_id].move_to(x, y)

    def tick(self) -> None:
        self.tick_count += 1
        self.print_area()
        self.next_time += self.TICK_INTERVAL

    def run(self) -> None:
        try:
            while self.active:
                time.sleep(self.next_time - time.time())
                if self.messages:
                    self.handle_message(self.messages.pop(0))
                for port in list(self.robot_connections.keys()):
                    try:
                        self.send(port, "PING")
                    except BrokenPipeError:
                        self.robots[port].is_connected = False
                self.tick()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()


if __name__ == "__main__":
    Sim().run()
