#!/usr/bin/env python3
from typing import Iterable, List, Tuple
import sqlite3
import re


connection = sqlite3.connect("db/ldb.db")
cursor = connection.cursor()


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


robots_count = fetch_env_count("robots_count", cursor)
robot_bcs_blocker: List[List[str]] = [[] for _ in range(robots_count)]
robot_bws_blocker: List[List[str]] = [[] for _ in range(robots_count)]

robot_columns = ["robot_location", "ongoing_action"]


def search_bcs(robot_name: str) -> str:
    global robot_bcs_blocker
    free_BCS = ""
    blocked_BCS: List[int] = []
    available_BCS: List[str] = []

    connection = sqlite3.connect("db/ldb.db")
    cursor = connection.cursor()
    robot_number = int(re.search(r"\d+", robot_name).group())
    robot_location = fetch_robot_location(robot_name, cursor)
    if "BCS_" in robot_location:
        bcs_number = re.search(r"\d+", robot_location).group()
        bcs_station = "BCS_" + str(bcs_number)
        if bcs_station not in robot_bcs_blocker[robot_number - 1]:
            robot_bcs_blocker[robot_number - 1].append(bcs_station)

    with connection:
        robot_column_values = fetch_all(robot_columns, "robot_info", cursor)
        for each_row in robot_column_values:
            for value in each_row:
                if "BCS_" in value:
                    bcs_number = re.search(r"\d+", value).group()
                    blocked_BCS.append(int(bcs_number))

        cart_column_values = fetch_all("cart_location", "cart_info", cursor)
        for each_row in cart_column_values:
            for value in each_row:
                if "BCS_" in value:
                    bcs_number = re.search(r"\d+", value).group()
                    blocked_BCS.append(int(bcs_number))

        bcs_count = fetch_env_count("BCS_count", cursor)
        for bcs in range(1, bcs_count + 1):
            if bcs not in blocked_BCS:
                available_BCS.append("BCS_" + str(bcs))

        # Choosing the first value in available_bcs that is not in the robot's blocker
        for choice in available_BCS:
            if choice not in robot_bcs_blocker[robot_number - 1]:
                free_BCS = choice
                robot_bcs_blocker[robot_number - 1].append(free_BCS)
                break

        return free_BCS


def search_bws(robot_name: str) -> str:
    global robot_bws_blocker
    free_BWS = ""
    blocked_BWS: List[int] = []
    available_BWS: List[str] = []

    connection = sqlite3.connect("db/ldb.db")
    cursor = connection.cursor()
    robot_number = int(re.search(r"\d+", robot_name).group())
    robot_location = fetch_robot_location(robot_name, cursor)
    if "BWS_" in robot_location:
        bws_number = re.search(r"\d+", robot_location).group()
        bws_station = "BWS_" + str(bws_number)
        if bws_station not in robot_bws_blocker[robot_number - 1]:
            robot_bws_blocker[robot_number - 1].append(bws_station)

    with connection:
        robot_column_values = fetch_all(robot_columns, "robot_info", cursor)
        for each_row in robot_column_values:
            for value in each_row:
                if "BWS_" in value:
                    bws_number = re.search(r"\d+", value).group()
                    blocked_BWS.append(int(bws_number))

        cart_column_values = fetch_all("cart_location", "cart_info", cursor)
        for each_row in cart_column_values:
            for value in each_row:
                if "BWS_" in value:
                    bws_number = re.search(r"\d+", value).group()
                    blocked_BWS.append(int(bws_number))

        bws_count = fetch_env_count("BWS_count", cursor)
        for bws in range(1, bws_count + 1):
            if bws not in blocked_BWS:
                available_BWS.append("BWS_" + str(bws))

        # Choosing the first value in available_bws that is not in the robot's blocker
        for choice in available_BWS:
            if choice not in robot_bws_blocker[robot_number - 1]:
                free_BWS = choice
                robot_bws_blocker[robot_number - 1].append(free_BWS)
                break

        return free_BWS


def reset_bcs_blocker(robot_name):
    global robot_bcs_blocker
    robot_number = int(re.search(r"\d+", robot_name).group())
    robot_bcs_blocker[robot_number - 1] = []
    return True


def reset_bws_blocker(robot_name):
    global robot_bws_blocker
    robot_number = int(re.search(r"\d+", robot_name).group())
    robot_bws_blocker[robot_number - 1] = []
    return True
