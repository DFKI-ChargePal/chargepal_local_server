from typing import Dict, List, Optional, Tuple
import os
import sqlite3


db_path = os.path.join(os.path.dirname(__file__), "db/ldb.db")
connection = sqlite3.connect(db_path)
cursor = connection.cursor()


def connect(path: Optional[str] = None) -> None:
    """(Re-)Connect to ldb at path if given, else the global db_path."""
    global db_path, connection, cursor
    if path:
        db_path = path
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()


def show_tables(print_results: bool=True) -> List[Tuple[str, ...]]:
    """Print all tables in the ldb."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    results = cursor.fetchall()
    if print_results:
        print(results)
    return results


def select(sql: str, print_results: bool=True) -> List[Tuple[str, ...]]:
    """
    Print results of a "SELECT <sql>;" statement.
    If no "FROM" keyword is used, "* FROM " is prepended.

    Examples:
    select("robot_name from robot_info")
    select("orders_in where charging_session_status = 'checked_in'")
    """
    if " FROM " not in sql.upper():
        sql = "* FROM " + sql
    try:
        sql = f"SELECT {sql};"
        connection.commit()
        cursor.execute(sql)
        header = str(tuple(entries[0] for entries in cursor.description))
        results = cursor.fetchall()
        if print_results:
            print(header)
            print("-" * len(header))
            for entries in results:
                print(entries)
        return results
    except sqlite3.Error as e:
        print(sql)
        print(f"sqlite3.{type(e).__name__}: {e}")
        return []


def update(sql: str) -> None:
    """
    Execute a "UPDATE <sql>; statement.
    Usage of the "WHERE" keyword is mandatory.

    Example:
    update("robot_info set robot_location = 'ADS_1' where robot_name = 'ChargePal1'")
    """
    sql = f"UPDATE {sql};"
    if " WHERE " not in sql.upper():
        print(sql)
        print('Error: Usage of the "WHERE" keyword is mandatory.')
        return

    try:
        cursor.execute(sql)
        connection.commit()
    except sqlite3.Error as e:
        print(sql)
        print(f"sqlite3.{type(e).__name__}: {e}")


def update_locations(
    locations_by_names: Dict[str, str], cart_prefix: str = "BAT_"
) -> None:
    """
    Execute a
    "UPDATE cart_info SET cart_location = '<location>' WHERE cart_name = '<name>';"
    statement for each "<name>: <location>" dict entry where name.startswith(cart_prefix).
    Execute a
    "UPDATE robot_info SET robot_location = '<location>' WHERE robot_name = '<name>';"
    statement for all other "<name>: <location>" entries each.

    Example:
    update_locations({"ChargePal1": "ADS_1", "BAT_1": "ADS_1"})
    """
    for name, location in locations_by_names.items():
        if name.startswith(cart_prefix):
            update(
                f"cart_info SET cart_location = '{location}' WHERE cart_name = '{name}'"
            )
        else:
            update(
                f"robot_info SET robot_location = '{location}' WHERE robot_name = '{name}'"
            )
