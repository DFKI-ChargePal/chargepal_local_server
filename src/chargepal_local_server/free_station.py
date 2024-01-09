#!/usr/bin/env python3
import sqlite3
import re


connection = sqlite3.connect("db/ldb.db")
cursor = connection.cursor()
cursor.execute("SELECT count FROM env_info WHERE info = 'robots_count';")
robots_count = cursor.fetchone()[0]
robot_bcs_blocker = [[] for _ in range(robots_count)]
robot_bws_blocker = [[] for _ in range(robots_count)]

robot_columns = ["robot_location", "ongoing_action"]


def search_bcs(robot_name):
    global robot_bcs_blocker
    free_BCS = ""
    blocked_BCS = []
    available_BCS = []

    connection = sqlite3.connect("db/ldb.db")
    cursor = connection.cursor()
    robot_number = int(re.search(r"\d+", robot_name).group())
    cursor.execute(
        "SELECT robot_location FROM robot_info WHERE robot_name = robot_name;"
    )
    robot_position = cursor.fetchone()[0]
    if "BCS_" in robot_position:
        bcs_number = re.search(r"\d+", robot_position).group()
        bcs_station = "BCS_" + str(bcs_number)
        if bcs_station not in robot_bcs_blocker[robot_number - 1]:
            robot_bcs_blocker[robot_number - 1].append(bcs_station)

    with connection:
        columns_str = ", ".join(robot_columns)
        cursor.execute(f"SELECT {columns_str} FROM robot_info;")
        robot_column_values = cursor.fetchall()
        for each_row in robot_column_values:
            for value in each_row:
                if "BCS_" in value:
                    bcs_number = re.search(r"\d+", value).group()
                    blocked_BCS.append(int(bcs_number))

        cursor.execute(f"SELECT {'cart_location'} FROM cart_info;")
        cart_column_values = cursor.fetchall()

        for each_row in cart_column_values:
            for value in each_row:
                if "BCS_" in value:
                    bcs_number = re.search(r"\d+", value).group()
                    blocked_BCS.append(int(bcs_number))

        cursor.execute("SELECT count FROM env_info WHERE info = 'BCS_count';")
        bcs_count = cursor.fetchone()[0]
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


def search_bws(robot_name):
    global robot_bws_blocker
    free_BWS = ""
    blocked_BWS = []
    available_BWS = []

    connection = sqlite3.connect("db/ldb.db")
    cursor = connection.cursor()
    robot_number = int(re.search(r"\d+", robot_name).group())
    cursor.execute(
        "SELECT robot_location FROM robot_info WHERE robot_name =robot_name;"
    )
    robot_position = cursor.fetchone()[0]
    if "BWS_" in robot_position:
        bws_number = re.search(r"\d+", robot_position).group()
        bws_station = "BWS_" + str(bws_number)
        if bws_station not in robot_bws_blocker[robot_number - 1]:
            robot_bws_blocker[robot_number - 1].append(bws_station)

    with connection:
        columns_str = ", ".join(robot_columns)
        cursor.execute(f"SELECT {columns_str} FROM robot_info;")
        robot_column_values = cursor.fetchall()
        for each_row in robot_column_values:
            for value in each_row:
                if "BWS_" in value:
                    bws_number = re.search(r"\d+", value).group()
                    blocked_BWS.append(int(bws_number))

        cursor.execute(f"SELECT {'cart_location'} FROM cart_info;")
        cart_column_values = cursor.fetchall()

        for each_row in cart_column_values:
            for value in each_row:
                if "BWS_" in value:
                    bws_number = re.search(r"\d+", value).group()
                    blocked_BWS.append(int(bws_number))

        cursor.execute("SELECT count FROM env_info WHERE info = 'BWS_count';")
        bws_count = cursor.fetchone()[0]
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
