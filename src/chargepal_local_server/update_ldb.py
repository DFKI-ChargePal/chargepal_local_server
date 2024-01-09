#!/usr/bin/env python3
import sqlite3
import ast
import os

current_directory = os.getcwd()


def update(table_name, string_rdb_data):

    rows_data = ast.literal_eval(string_rdb_data)

    with sqlite3.connect(current_directory + "/db/ldb.db") as ldb_connection:
        ldb_cursor = ldb_connection.cursor()
        if table_name == "robot_info":
            for row in rows_data:
                ldb_cursor.execute(
                    "DELETE FROM robot_info WHERE robot_name = ?", (row[0],)
                )  # 'robot_name' is in the first column

            ldb_cursor.executemany(
                "INSERT INTO robot_info VALUES (?,?,?,?,?,?,?) ", rows_data
            )
        elif table_name == "cart_info":
            for row in rows_data:
                ldb_cursor.execute(
                    "DELETE FROM cart_info WHERE cart_name = ?", (row[0],)
                )  # 'robot_name' is in the first column

            ldb_cursor.executemany(
                "INSERT INTO cart_info VALUES (?,?,?,?,?) ", rows_data
            )

        ldb_connection.commit()

    return True
