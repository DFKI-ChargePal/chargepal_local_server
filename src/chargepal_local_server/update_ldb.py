from typing import List, Tuple
import sqlite3
import ast
import os

current_directory = os.getcwd()


def update(table_name: str, string_rdb_data: str) -> None:
    rows_data: List[Tuple[object, ...]] = ast.literal_eval(string_rdb_data)
    with sqlite3.connect(current_directory + "/db/ldb.db") as ldb_connection:
        ldb_cursor = ldb_connection.cursor()

        ldb_cursor.execute(
            f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        table_definition = ldb_cursor.fetchone()[0]
        # Extract column names from the table definition
        column_names = [
            part.split()[0]
            for part in table_definition.split("(")[1].split(",")
            if "rowid" not in part
        ]
        set_columns = ", ".join([f"{column_name} = ?" for column_name in column_names])

        if table_name == "robot_info":
            for row in rows_data:
                r_name = row[0]

                ldb_cursor.execute(
                    f"SELECT * FROM {table_name} WHERE robot_name = ?", (r_name,)
                )
                result_robot = ldb_cursor.fetchone()

                if result_robot:
                    ldb_cursor.execute(
                        f"UPDATE {table_name} SET {set_columns} WHERE robot_name = ?",
                        row[0:] + (row[0],),
                    )

        elif table_name == "cart_info":
            for row in rows_data:
                c_name = row[0]

                ldb_cursor.execute(
                    f"SELECT * FROM {table_name} WHERE cart_name = ?", (c_name,)
                )
                result_cart = ldb_cursor.fetchone()

                if result_cart:
                    ldb_cursor.execute(
                        f"UPDATE {table_name} SET {set_columns} WHERE cart_name = ?",
                        row[0:] + (row[0],),
                    )

        ldb_connection.commit()

    return True
