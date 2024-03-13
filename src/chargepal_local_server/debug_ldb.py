from typing import Dict, List, Optional, Tuple
import os
import re
import sqlite3


db_filepath = os.path.join(os.path.dirname(__file__), "db/ldb.db")
connection = sqlite3.connect(db_filepath)
cursor = connection.cursor()


def connect(filepath: Optional[str] = None) -> None:
    """(Re-)Connect to database at filepath if given, else to the global db_filepath."""
    global db_filepath, connection, cursor
    if filepath:
        db_filepath = filepath
    connection = sqlite3.connect(db_filepath)
    cursor = connection.cursor()


def show_tables() -> List[str]:
    """Return all table names."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table';")
    results: List[str] = [entries[0] for entries in cursor.fetchall()]
    return results


def delete_from(sql: str) -> None:
    """
    Execute a "DELETE FROM <sql>;" statement.

    Example:
    delete_from("orders_in where charging_session_id = 1079")
    """
    sql = f"DELETE FROM {sql};"
    try:
        cursor.execute(sql)
        connection.commit()
    except sqlite3.Error as e:
        print(sql)
        print(f"sqlite3.{type(e).__name__}: {e}")


def select(sql: str) -> List[Tuple[object, ...]]:
    """
    Return results of a "SELECT <sql>;" statement.
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
        results = cursor.fetchall()
        return results
    except sqlite3.Error as e:
        print(sql)
        print(f"sqlite3.{type(e).__name__}: {e}")
        return []


def print_select(sql: str) -> None:
    """
    Print results of a "SELECT <sql>;" statement with table headers.
    If no "FROM" keyword is used, "* FROM " is prepended.
    """
    results = select(sql)
    header = str(tuple(entries[0] for entries in cursor.description))
    print(header)
    print("-" * len(header))
    for entries in results:
        print(entries)


def update(sql: str) -> None:
    """
    Execute a "UPDATE <sql>;" statement.

    Example:
    update("robot_info set robot_location = 'ADS_1' where robot_name = 'ChargePal1'")
    """
    sql = f"UPDATE {sql};"
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

    def __repr__(self) -> str:
        entries: List[Tuple[str, int]] = select("env_info")
        return str({f"{name.replace('_count', '')}": count for name, count in entries})

    @staticmethod
    def select(prefix: str) -> int:
        return select(f"count FROM env_info WHERE info = '{prefix}_count'")

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
