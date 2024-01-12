#!/usr/bin/env python3
from typing import Dict, Iterable, List, Set, Tuple, Union
from collections import defaultdict
import sqlite3
import re


def fetch_env_count(count_name: str, cursor: sqlite3.Cursor) -> int:
    """Return count for count_name from env_info of ldb."""
    cursor.execute(f"SELECT count FROM env_info WHERE info = '{count_name}';")
    return int(cursor.fetchone()[0])


def fetch_robot_location(robot_name: str, cursor: sqlite3.Cursor) -> str:
    """Return robot location for robot_name from robot_info of ldb."""
    cursor.execute(
        f"SELECT robot_location FROM robot_info WHERE robot_name = '{robot_name}'"
    )
    return str(cursor.fetchone()[0])


def fetch_all(
    columns_str: Union[str, Iterable[str]], table: str, cursor: sqlite3.Cursor
) -> List[Tuple[str, ...]]:
    """Return all entries for columns_str from table of ldb."""
    if not isinstance(columns_str, str):
        columns_str = ", ".join(columns_str)
    cursor.execute(f"SELECT {columns_str} FROM {table};")
    return cursor.fetchall()


robot_blockers: Dict[str, Dict[str, Set[str]]] = {
    prefix: defaultdict(set) for prefix in ("BCS_", "BWS_")
}

robot_columns = ["robot_location", "ongoing_action"]


def get_station_name(string: str, station_prefix: str) -> str:
    """Return station name with station_prefix from string."""
    return re.search(rf"{station_prefix}(\d+)", string).group()


def search_free_station(robot_name: str, station_prefix: str) -> str:
    """
    Return a free station with station_prefix for robot_name,
     or an empty str if there is none.
    """
    free_station = ""
    blocked_stations: Set[str] = set()

    connection = sqlite3.connect("db/ldb.db")
    cursor = connection.cursor()
    # Determine station_name from current robot_location
    #  and add it to this robot's blockers.
    robot_location = fetch_robot_location(robot_name, cursor)
    if station_prefix in robot_location:
        robot_blockers[station_prefix][robot_name].add(
            get_station_name(robot_location, station_prefix)
        )

    with connection:
        # Fetch all stations blocked by robots.
        robot_column_values = fetch_all(robot_columns, "robot_info", cursor)
        for each_row in robot_column_values:
            for value in each_row:
                if station_prefix in value:
                    blocked_stations.add(get_station_name(value, station_prefix))

        # Fetch all stations blocked by carts.
        cart_column_values = fetch_all("cart_location", "cart_info", cursor)
        for each_row in cart_column_values:
            for value in each_row:
                if station_prefix in value:
                    blocked_stations.add(get_station_name(value, station_prefix))

        # Choose the first available station that is not in the robot's blocker.
        station_count = fetch_env_count(station_prefix + "count", cursor)
        for station_number in range(1, station_count + 1):
            station_name = f"{station_prefix}{station_number}"
            if (
                station_name not in blocked_stations
                and station_name not in robot_blockers[station_prefix][robot_name]
            ):
                free_station = station_name
                robot_blockers[station_prefix][robot_name].add(free_station)
                break

    return free_station


def reset_blockers(robot_name: str, station_prefix: str) -> bool:
    """Clear the blockers for robot_name and stations with station_prefix."""
    robot_blockers[station_prefix][robot_name].clear()
    return True
