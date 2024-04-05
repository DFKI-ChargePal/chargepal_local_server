#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Gurunatraj Parthasarathy
Email: gurunatraj.parthasarathy@dfki.de
"""
import os
import sqlite3


def main(robots_count: int = 1, carts_count: int = 1):

    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "db/ldb.db"))
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
            cart_charge FLOAT,
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

    cursor.execute("DELETE FROM orders_in")

    cursor.execute("DELETE FROM robot_info")
    for number in range(1, robots_count + 1):
        robot_data = (f"ChargePal{number}", f"RBS_{number}", "none", "none", "none", "none", 0.0, 0)
        cursor.execute(
            "INSERT INTO robot_info (robot_name,robot_location, current_job, ongoing_action, previous_action, cart_on_robot,robot_charge,error_count) VALUES (?,?,?,?,?,?,?,?)",
            robot_data,
        )

    cursor.execute("DELETE FROM cart_info")
    for number in range(1, carts_count + 1):
        cart_data = (f"BAT_{number}", f"BWS_{number}", "none", "none", 0.0, 0)
        cursor.execute(
            "INSERT INTO cart_info (cart_name,cart_location, robot_on_cart, plugged, cart_charge, error_count) VALUES (?,?,?,?,?,?)",
            cart_data,
        )

    RBS_count = ("RBS_count", 1)
    ADS_count = ("ADS_count", 1)
    BCS_count = ("BCS_count", 0)
    BWS_count = ("BWS_count", 1)
    cursor.execute("DELETE FROM env_info")
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", ("robots_count", robots_count))
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", ("carts_count", carts_count))
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", RBS_count)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", ADS_count)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", BCS_count)
    cursor.execute("INSERT INTO env_info (info,count) VALUES (?,?)", BWS_count)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
