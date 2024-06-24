from typing import List, Tuple
import sqlite3
import ast
import os

current_directory = os.getcwd()


def update(packaged_strings: List[str]) -> bool:
    
    with sqlite3.connect(current_directory + "/db/ldb.db") as ldb_connection:
        ldb_cursor = ldb_connection.cursor()

        for package in packaged_strings:
            
            table_name, string_rdb_data = package.split(":", 1)
            rows_data: List[Tuple[object, ...]] = ast.literal_eval(string_rdb_data)
         
            table_name = (
                "cart_info" if table_name == "battery_action_info" else table_name
            )
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
            column_set = set(column_names)

            if table_name == "robot_info":
                for row in rows_data:
                    r_name = row[0]
                    row_data = dict(zip(column_names, row))

                    # Only update columns that exist in both the table and row data
                    update_columns = [col for col in column_names if col in row_data]
                    update_values = [row_data[col] for col in update_columns]

                    set_columns = ", ".join([f"{col} = ?" for col in update_columns])

                    ldb_cursor.execute(
                        f"SELECT * FROM {table_name} WHERE name = ?", (r_name,)
                    )
                    result_robot = ldb_cursor.fetchone()

                    if result_robot:
                        ldb_cursor.execute(
                            f"UPDATE {table_name} SET {set_columns} WHERE name = ?",
                            update_values + [r_name],
                        )

            elif table_name == "cart_info":
                for row in rows_data:
                    c_name = row[0]
                    row_data = dict(zip(column_names, row))
                    print(row_data)
                    # Only update columns that exist in both the table and row data
                    update_columns = [col for col in column_names if col in row_data]
                    update_values = [row_data[col] for col in update_columns]

                    set_columns = ", ".join([f"{col} = ?" for col in update_columns])
                    print(set_columns)
                    ldb_cursor.execute(
                        f"SELECT * FROM {table_name} WHERE name = ?", (c_name,)
                    )
                    result_cart = ldb_cursor.fetchone()

                    if result_cart:
                        ldb_cursor.execute(
                            f"UPDATE {table_name} SET {set_columns} WHERE name = ?",
                            update_values + [c_name],
                        )

        ldb_connection.commit()

    return True


""" 

def update(string_rdb_data: str) -> None:
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
                    f"SELECT * FROM {table_name} WHERE name = ?", (r_name,)
                )
                result_robot = ldb_cursor.fetchone()

                if result_robot:
                    ldb_cursor.execute(
                        f"UPDATE {table_name} SET {set_columns} WHERE name = ?",
                        row[0:] + (row[0],),
                    )

        elif table_name == "cart_info":
            for row in rows_data:
                c_name = row[0]

                ldb_cursor.execute(
                    f"SELECT * FROM {table_name} WHERE name = ?", (c_name,)
                )
                result_cart = ldb_cursor.fetchone()

                if result_cart:
                    ldb_cursor.execute(
                        f"UPDATE {table_name} SET {set_columns} WHERE name = ?",
                        row[0:] + (row[0],),
                    )
        elif table_name == "battery_actions_info" :
            pass

        ldb_connection.commit()

    return True
 """
