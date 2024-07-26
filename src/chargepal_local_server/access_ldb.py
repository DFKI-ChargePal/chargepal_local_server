#!/usr/bin/env python3
from typing import Dict, Iterable, List, Optional, Tuple, Type, Union
from types import TracebackType
from datetime import datetime, timedelta
from chargepal_local_server.pdb_interfaces import to_str
import mysql.connector
import mysql.connector.cursor
import os
import re
import sqlite3
import yaml


SQLITE_DB_FILEPATH = os.path.join(os.path.dirname(__file__), "db/ldb.db")
MYSQL_CONFIG_FILEPATH = os.path.expanduser("~/.my.cnf")


ALL_BOOKING_HEADERS = (
    "charging_session_id",
    "app_id",
    "customer_id",
    "VIN",
    "bev_chargePower_kW_AC_I",
    "bev_chargePower_kW_AC_II",
    "bev_charge_Port_AC",
    "bev_fastcharge_power_DC_I",
    "bev_fastcharge_power_DC_II",
    "bev_fastcharge_port",
    "bev_Port_Location",
    "drop_location",
    "BEV_slot_planned",
    "plugintime_calculated",
    "target_soc_pct",
    "current_BEV_slot_recond",
    "drop_date_time",
    "pick_up_date_time",
    "arrival_timestamp",
    "booking_date_time_dev",
    "charging_session_status",
    "last_change",
    "immediate_charge",
    "Actual_Drop_SOC",
    "Actual_Target_SOC",
    "Actual_plugintime_calculated",
    "Actual_BEV_Drop_Time",
    "Actual_BEV_Pickup_Time",
)


def datetime_str(
    now: Optional[datetime] = None,
    weeks: int = 0,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    """
    Return str representation in datetime format of now with an offset of
    weeks, days, hours, minutes, and seconds.
    """
    if now is None:
        now = datetime.now()
    if weeks or days or hours or minutes or seconds:
        now += timedelta(
            weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds
        )
    return now.isoformat(sep=" ", timespec="seconds")


def time_str(
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)


def parse_any(obj: object) -> object:
    """Parse any str into its supported object type."""
    if isinstance(obj, str):
        if re.match(r"(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)$", obj):
            return datetime.strptime(obj, "%Y-%m-%d %H:%M:%S")
        if re.match(r"(\d+):(\d+):(\d+)$", obj):
            hours_str, minutes_str, seconds_str = obj.split(":")
            return timedelta(
                hours=float(hours_str),
                minutes=float(minutes_str),
                seconds=float(seconds_str),
            )
        if obj.isnumeric() and not obj.startswith("0"):
            return float(obj) if "." in obj else int(obj)
    return obj


class SQLite3Access:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(SQLITE_DB_FILEPATH)
        self.cursor = self.connection.cursor()

    def __enter__(self) -> sqlite3.Cursor:
        return self.cursor

    def __exit__(
        self,
        exception_type: Type[BaseException],
        exception_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        self.connection.commit()
        self.connection.close()


class MySQLAccess:
    def __init__(self) -> None:
        self.connection = mysql.connector.connect(
            read_default_file=MYSQL_CONFIG_FILEPATH,
            host="localhost",
            database="LSV0002_DB",
        )
        self.cursor = self.connection.cursor()

    def __enter__(self) -> mysql.connector.cursor.MySQLCursor:
        return self.cursor

    def __exit__(
        self,
        exception_type: Type[BaseException],
        exception_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        self.connection.commit()
        self.connection.close()

    @staticmethod
    def is_configured() -> bool:
        return os.path.isfile(MYSQL_CONFIG_FILEPATH)


class LDB:
    @staticmethod
    def get() -> Union[SQLite3Access, MySQLAccess]:
        """Return a MySQLAccess if the MySQL config file exists, else a SQLite3Access."""
        return MySQLAccess() if MySQLAccess.is_configured() else SQLite3Access()

    @classmethod
    def fetch_by_first_header(
        cls, table: str, headers: Iterable[str]
    ) -> Dict[str, Dict[str, object]]:
        """
        Return from ldb a dict for the first header in each row
        consisting of the remaining headers and entries.
        """
        with cls.get() as cursor:
            cursor.execute(f"SELECT {', '.join(headers)} FROM {table};")
            return {
                entries[0]: {
                    header: entry for header, entry in zip(headers[1:], entries[1:])
                }
                for entries in cursor.fetchall()
            }

    @staticmethod
    def fetch_env_infos() -> Dict[str, List[str]]:
        """Return a dict of names and values from env_info in ldb."""
        with SQLite3Access() as cursor:
            cursor.execute("SELECT name, value FROM env_info;")
            return {name: yaml.safe_load(value) for name, value in cursor.fetchall()}

    @staticmethod
    def fetch_env_count(name: str) -> int:
        """Return the count for name from env_info in ldb."""
        with SQLite3Access() as cursor:
            cursor.execute(f"SELECT count FROM env_info WHERE name = '{name}';")
            return int(cursor.fetchone()[0])

    @classmethod
    def fetch_updated_bookings(
        cls, headers: Iterable[str], threshold: datetime = datetime.min
    ) -> List[Dict[str, object]]:
        """
        Return from orders_in in ldb a dict of headers and entries
        for which last_change is greater than or equal to threshold.

        Note: You must handle updates within the same second.
        """
        with cls.get() as cursor:
            cursor.execute(
                f"SELECT {', '.join(headers)} FROM orders_in"
                f" WHERE last_change >= '{threshold}';"
            )
            all_entries = cursor.fetchall()
        return [
            {header: parse_any(entry) for header, entry in zip(headers, entries)}
            for entries in all_entries
        ]

    @classmethod
    def delete_bookings(cls) -> None:
        """Delete all bookings from orders_in in ldb."""
        with cls.get() as cursor:
            cursor.execute("DELETE FROM orders_in")

    @staticmethod
    def update_location(location: str, robot: str, cart: Optional[str] = None) -> None:
        """Update location of robot and cart in ldb."""  #
        with SQLite3Access() as cursor:
            cursor.execute(
                f"UPDATE robot_info SET robot_location = '{location}'"
                f" WHERE name = '{robot}';"
            )
            if cart:
                cursor.execute(
                    f"UPDATE cart_info SET cart_location = '{location}'"
                    f" WHERE name = '{cart}';"
                )

    @classmethod
    def get_session_statuses(cls) -> List[Tuple[int, str]]:
        """Return list of (charging_session_id, charging_session_status) from ldb."""
        with cls.get() as cursor:
            cursor.execute("SELECT charging_session_id, charging_session_status FROM orders_in;")
            return cursor.fetchall()

    @classmethod
    def update_session_status(
        cls, charging_session_id: int, charging_session_status: str
    ) -> None:
        """Update charging_session_status for charging_session_id in ldb."""
        with cls.get() as cursor:
            cursor.execute(
                f"UPDATE orders_in SET charging_session_status = '{charging_session_status}'"
                f" WHERE charging_session_id = '{charging_session_id}';"
            )
            cursor.execute(
                f"UPDATE orders_in SET last_change = '{datetime_str()}'"
                f" WHERE charging_session_id = '{charging_session_id}';"
            )

    @staticmethod
    def update_battery(table: str, battery_id: str, **kwargs: object) -> None:
        """Update table for Battry_ID in lsv_db as well as automatically update column 'last_change'."""
        sql_operation = f"UPDATE {table} SET last_change = '{datetime_str()}'"
        for key, value in kwargs.items():
            sql_operation += f", {key} = {to_str(value)}"
        sql_operation += f" WHERE Battry_ID = '{battery_id}';"
        print(sql_operation)
        try:
            with MySQLAccess() as cursor:
                cursor.execute(sql_operation)
        except mysql.connector.errors.Error as e:
            print(e)


if __name__ == "__main__":
    bookings = LDB.fetch_updated_bookings(ALL_BOOKING_HEADERS)
    print(bookings)
    if bookings:
        print(bookings[-1]["charging_session_status"])
        print(bookings[-1]["drop_date_time"])
