from typing import List, Tuple
import sqlite3
import ast
import os

current_directory = os.getcwd()


def update(packaged_strings: List[str]) -> bool:
    with sqlite3.connect(current_directory + "/db/ldb.db") as ldb_connection:
        ldb_cursor = ldb_connection.cursor()

        for data_package_str in packaged_strings:
            data_package: List[Tuple[object, ...]] = ast.literal_eval(data_package_str)
            for table_name, table_data in data_package.items():
                if table_name == "battery_action_info":
                    table_name = "cart_info"

                for row_name, row_data in table_data.items():
                    update_columns = []
                    update_values = []
                    for column_name, value in row_data.items():

                        update_columns.append(column_name)
                        update_values.append(value)

                set_columns = ", ".join([f"{col} = ?" for col in update_columns])

                ldb_cursor.execute(
                    f"SELECT * FROM {table_name} WHERE name = ?", (row_name,)
                )
                result = ldb_cursor.fetchone()

                if result:
                    ldb_cursor.execute(
                        f"UPDATE {table_name} SET {set_columns} WHERE name = ?",
                        update_values + [row_name],
                    )

            ldb_connection.commit()

    return True
