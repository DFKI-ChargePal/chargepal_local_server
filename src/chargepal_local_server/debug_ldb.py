from typing import Dict, List, Optional, Tuple
import os
import re
import sqlite3


def get_db_filepath(reference_path: str, filename: str) -> str:
    """
    Compose path to db file using reference_path's directory name, "db/", and filename.
    """
    return os.path.join(os.path.dirname(reference_path), "db/", filename)


db_path = get_db_filepath(__file__, "ldb.db")
connection = sqlite3.connect(db_path)
cursor = connection.cursor()


def connect(path: Optional[str] = None) -> None:
    """(Re-)Connect to ldb at path if given, else the global db_path."""
    global db_path, connection, cursor
    if path:
        db_path = path
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()


def show_tables(print_results: bool = False) -> List[Tuple[str, ...]]:
    """Print all tables in the ldb."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    results = cursor.fetchall()
    if print_results:
        print(results)
    return results


def delete_table(table: str) -> None:
    """Delete all entries from table."""
    cursor.execute("DELETE FROM orders_in;")
    connection.commit()


def select(sql: str, print_results: bool = False) -> List[Tuple[str, ...]]:
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
    statement for each other "<name>: <location>" entry.

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


class ParkingAreaCounts:
    """
    Get or set counts in the env_info table.

    Examples:
    counts.robots
    counts.carts = 2
    counts.set("robots 1 carts: 2, RBS = 3; ADS4 and BCS:5 BWS=6")
    """

    @staticmethod
    def select(prefix: str) -> int:
        return select(
            f"count FROM env_info WHERE info = '{prefix}_count'", print_results=False
        )

    @staticmethod
    def update(prefix: str, value: int) -> None:
        update(f"env_info SET count = {value} WHERE info = '{prefix}_count'")

    @property
    def robots(self) -> int:
        return self.select("robots")[0][0]

    @robots.setter
    def robots(self, value: int) -> None:
        return self.update("robots", value)

    @property
    def carts(self) -> int:
        return self.select("carts")[0][0]

    @carts.setter
    def carts(self, value: int) -> None:
        return self.update("carts", value)

    @property
    def RBS(self) -> int:
        return self.select("RBS")[0][0]

    @RBS.setter
    def RBS(self, value: int) -> None:
        return self.update("RBS", value)

    @property
    def ADS(self) -> int:
        return self.select("ADS")[0][0]

    @ADS.setter
    def ADS(self, value: int) -> None:
        return self.update("ADS", value)

    @property
    def BCS(self) -> int:
        return self.select("BCS")[0][0]

    @BCS.setter
    def BCS(self, value: int) -> None:
        return self.update("BCS", value)

    @property
    def BWS(self) -> int:
        return self.select("BWS")[0][0]

    @BWS.setter
    def BWS(self, value: int) -> None:
        return self.update("BWS", value)

    def set(self, string: str) -> None:
        for prefix, count in re.findall(r"([A-Za-z]+)\s*[\:\=]?\s*(\d+)", string):
            self.update(prefix, int(count))


counts = ParkingAreaCounts()
