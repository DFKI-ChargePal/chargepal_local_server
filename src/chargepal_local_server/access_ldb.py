#!/usr/bin/env python3
from typing import Dict, Iterable, List, Optional, Type
from types import TracebackType
from datetime import datetime, timedelta
import mysql.connector
import mysql.connector.cursor
import os
import re
import sqlite3


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
    def __init__(self, ldb_filepath: str) -> None:
        self.connection = sqlite3.connect(ldb_filepath)
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
            host="localhost",
            user="ChargePal",
            password="ChargePal3002!",
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


class DatabaseAccess:
    def __init__(self, ldb_filepath: Optional[str] = None) -> None:
        self.ldb_filepath = (
            ldb_filepath
            if ldb_filepath
            else os.path.join(os.path.dirname(__file__), "db/ldb.db")
        )
        try:
            with MySQLAccess():
                pass
        except mysql.connector.errors.Error:
            print(
                f"Warning: No MySQL database found, thus using '{self.ldb_filepath}' instead!"
            )

    def fetch_by_first_header(
        self, table: str, headers: Iterable[str]
    ) -> Dict[str, Dict[str, object]]:
        """
        Return from ldb a dict for the first header in each row
        consisting of the remaining headers and entries.
        """
        with SQLite3Access(self.ldb_filepath) as cursor:
            cursor.execute(f"SELECT {', '.join(headers)} FROM {table};")
            return {
                entries[0]: {
                    header: entry for header, entry in zip(headers[1:], entries[1:])
                }
                for entries in cursor.fetchall()
            }

    def fetch_env_infos(self) -> Dict[str, int]:
        """Return env_info in ldb as dict of names and counts."""
        with SQLite3Access(self.ldb_filepath) as cursor:
            cursor.execute("SELECT * FROM env_info;")
            return {header: count for header, count in cursor.fetchall()}

    def fetch_updated_bookings(
        self, headers: Iterable[str], threshold: datetime = datetime.min
    ) -> List[Dict[str, object]]:
        """
        Return from orders_in in lsv_db a dict of headers and entries
        for which last_change is greater than or equal to threshold.

        Note: You must handle updates within the same second.
        """
        sql_operation = (
            f"SELECT {', '.join(headers)} FROM orders_in"
            f" WHERE last_change >= '{threshold}';"
        )
        try:
            with MySQLAccess() as cursor:
                cursor.execute(sql_operation)
                all_entries = cursor.fetchall()
        except mysql.connector.errors.Error:
            with SQLite3Access(self.ldb_filepath) as cursor:
                cursor.execute(sql_operation)
                all_entries = cursor.fetchall()
        return [
            {header: parse_any(entry) for header, entry in zip(headers, entries)}
            for entries in all_entries
        ]

    def delete_bookings(self) -> None:
        """Delete all bookings from orders_in in lsv_db."""
        sql_operation = "DELETE FROM orders_in"
        try:
            with MySQLAccess() as cursor:
                cursor.execute(sql_operation)
        except mysql.connector.errors.Error:
            with SQLite3Access(self.ldb_filepath) as cursor:
                cursor.execute(sql_operation)

    def update_location(
        self, location: str, robot: str, cart: Optional[str] = None
    ) -> None:
        """Update location of robot and cart in ldb."""  #
        with SQLite3Access(self.ldb_filepath) as cursor:
            cursor.execute(
                f"UPDATE robot_info SET robot_location = '{location}'"
                f" WHERE name = '{robot}';"
            )
            if cart:
                cursor.execute(
                    f"UPDATE cart_info SET cart_location = '{location}'"
                    f" WHERE name = '{cart}';"
                )

    def update_session_status(
        self, charging_session_id: int, charging_session_status: str
    ) -> None:
        """Update charging_session_status for charging_session_id in lsv_db."""
        sql_status_operation = (
            f"UPDATE orders_in SET charging_session_status = '{charging_session_status}'"
            f" WHERE charging_session_id = {charging_session_id};"
        )
        sql_change_operation = (
            f"UPDATE orders_in SET last_change = '{datetime_str()}'"
            f" WHERE charging_session_id = {charging_session_id};"
        )
        try:
            with MySQLAccess() as cursor:
                cursor.execute(sql_status_operation)
                cursor.execute(sql_change_operation)
        except mysql.connector.errors.Error:
            with SQLite3Access(self.ldb_filepath) as cursor:
                cursor.execute(sql_status_operation)
                cursor.execute(sql_change_operation)


if __name__ == "__main__":
    access = DatabaseAccess()
    bookings = access.fetch_updated_bookings(ALL_BOOKING_HEADERS)
    print(bookings)
    if bookings:
        print(bookings[-1]["charging_session_status"])
        print(bookings[-1]["drop_date_time"])
