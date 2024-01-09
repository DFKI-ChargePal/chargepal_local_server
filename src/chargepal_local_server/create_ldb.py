#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Gurunatraj Parthasarathy
Email: gurunatraj.parthasarathy@dfki.de
"""
import sqlite3


def main():

    conn = sqlite3.connect("db/ldb.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS robot_info (
            robot_name TEXT,
            robot_location TEXT,
            current_job TEXT,
            ongoing_action TEXT,
            previous_action TEXT,
            cart_on_robot TEXT,
            robot_charge FLOAT,
            error_count INTEGER
        )
    """
    )
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS cart_info (
            cart_name TEXT,
            cart_location TEXT,
            robot_on_cart TEXT,
            plugged TEXT,
            error_count INTEGER
        )
     """
    )

    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS env_info (
            info TEXT,
            count INTEGER
        )
     """
    )

    # Insert a row of data
    robot_data_1 = ("ChargePal1", "RBS_1", "none", "none", "none", "none", 0.0, 0)
    robot_data_2 = ("ChargePal2", "RBS_2", "none", "none", "none", "none", 0.0, 0)
    cursor.execute(
        "INSERT INTO robot_info (robot_name,robot_location, current_job, ongoing_action, previous_action, cart_on_robot,robot_charge,error_count) VALUES (?,?,?,?,?,?,?,?)",
        robot_data_1,
    )
    cursor.execute(
        "INSERT INTO robot_info (robot_name,robot_location, current_job, ongoing_action, previous_action, cart_on_robot,robot_charge,error_count) VALUES (?,?,?,?,?,?,?,?)",
        robot_data_2,
    )

    cart_data_1 = ("BAT_1", "BWS_1", "none", "none", 0.0, 0)
    cart_data_2 = ("BAT_2", "BWS_2", "none", "none", 0.0, 0)
    cart_data_3 = ("BAT_3", "BWS_3", "none", "none", 0.0, 0)
    cursor.execute(
        "INSERT INTO cart_info (cart_name,cart_location, robot_on_cart, plugged, cart_charge, error_count) VALUES (?,?,?,?,?,?)",
        cart_data_1,
    )
    cursor.execute(
        "INSERT INTO cart_info (cart_name,cart_location, robot_on_cart, plugged, cart_charge, error_count) VALUES (?,?,?,?,?,?)",
        cart_data_2,
    )
    cursor.execute(
        "INSERT INTO cart_info (cart_name,cart_location, robot_on_cart, plugged, cart_charge, error_count) VALUES (?,?,?,?,?,?)",
        cart_data_3,
    )

    robots_count = ("robots_count", 3)
    carts_count = ("carts_count", 3)
    RBS_count = ("RBS_count", 2)
    ADS_count = ("ADS_count", 2)
    BCS_count = ("BCS_count", 2)
    BWS_count = ("BWS_count", 3)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", robots_count)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", carts_count)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", RBS_count)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", ADS_count)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", BCS_count)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", BWS_count)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
