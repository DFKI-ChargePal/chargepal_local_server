#!/usr/bin/env python3
from typing import Dict, Iterable, List, Set, Tuple
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
    columns_str: str | Iterable[str], table: str, cursor: sqlite3.Cursor
) -> List[Tuple[str, ...]]:
    """Return all entries for columns_str from table of ldb."""
    if not isinstance(columns_str, str):
        columns_str = ", ".join(columns_str)
    cursor.execute(f"SELECT '{columns_str}' FROM {table};")
    return cursor.fetchall()


robot_blockers: Dict[str, Dict[str, Set[str]]] = {
    prefix: defaultdict(set) for prefix in ("BCS_", "BWS_")
}

robot_columns = ["robot_location", "ongoing_action"]


def search_free_station(robot_name: str, station_prefix: str) -> str:
    free_station = ""
    blocked_stations: Set[str] = set()

    connection = sqlite3.connect("db/ldb.db")
    cursor = connection.cursor()
    robot_location = fetch_robot_location(robot_name, cursor)
    if station_prefix in robot_location:
        station_number = re.search(r"\d+", robot_location).group()
        station_name = station_prefix + str(station_number)
        robot_blockers[station_prefix][robot_name].add(station_name)

    with connection:
        robot_column_values = fetch_all(robot_columns, "robot_info", cursor)
        for each_row in robot_column_values:
            for value in each_row:
                if station_prefix in value:
                    blocked_stations.add(station_name)

        cart_column_values = fetch_all("cart_location", "cart_info", cursor)
        for each_row in cart_column_values:
            for value in each_row:
                if station_prefix in value:
                    blocked_stations.add(station_name)

        # Choosing the first available station that is not in the robot's blocker
        station_count = fetch_env_count(station_prefix + "count", cursor)
        for station_number in range(1, station_count + 1):
            station_name = f"{station_prefix}{station_number}"
            if station_name not in blocked_stations and station_name not in robot_blockers[station_prefix][robot_name]:
                free_station = station_name
                robot_blockers[station_prefix][robot_name].add(free_station)
                break

    return free_station


def reset_blockers(robot_name: str, station_prefix: str) -> bool:
    robot_blockers[station_prefix][robot_name].clear()
    return True
