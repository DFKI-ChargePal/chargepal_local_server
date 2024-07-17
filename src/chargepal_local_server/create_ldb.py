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
            name TEXT,
            robot_location TEXT,
            current_job_id INTEGER,
            current_job TEXT,
            ongoing_action TEXT,
            previous_action TEXT,
            cart_on_robot TEXT,
            job_status TEXT,
            availability BOOLEAN,
            robot_charge FLOAT,
            error_count INTEGER
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cart_info (
            name TEXT,
            cart_location TEXT,
            robot_on_cart TEXT,
            plugged TEXT,
            action_state TEXT,
            error_count INTEGER
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS env_info (
            name TEXT,
            value TEXT,
            count INTEGER
        )
        """
    )

    cursor.execute("DELETE FROM orders_in")

    cursor.execute("DELETE FROM robot_info")
    for number in range(1, robots_count + 1):
        robot_data = (f"ChargePal{number}", f"RBS_{number}",None, None, None, None, None,None,True, 0.0, 0)
        cursor.execute(
            "INSERT INTO robot_info (name,robot_location,current_job_id,current_job, ongoing_action, previous_action, cart_on_robot,job_status,availability,robot_charge,error_count) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            robot_data,
        )

    cursor.execute("DELETE FROM cart_info")
    for number in range(1, carts_count + 1):
        cart_data = (f"BAT_{number}", f"BWS_{number}", None, None,None, 0)
        cursor.execute(
            "INSERT INTO cart_info (name,cart_location, robot_on_cart, plugged,action_state, error_count) VALUES (?,?,?,?,?,?)",
            cart_data,
        )

    
    cursor.execute("DELETE FROM env_info")
    
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
