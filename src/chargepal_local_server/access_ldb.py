#!/usr/bin/env python3
from typing import Dict, Iterable, List, Optional
from datetime import datetime, timedelta
import sqlite3


BOOKING_HEADERS = (
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
ROBOT_INFO_HEADERS = (
    "robot_name",
    "robot_location",
    "current_job",
    "ongoing_action",
    "previous_action",
    "cart_on_robot",
    "robot_charge",
    "error_count",
)
CART_INFO_HEADERS = (
    "cart_name",
    "cart_location",
    "robot_on_cart",
    "plugged",
    "error_count",
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


def parse_datetime(string: str) -> datetime:
    """Return datetime from a str representing it."""
    return datetime.strptime(string, "%Y-%m-%d %H:%M:%S")


def time_str(
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)


def parse_time(string: str) -> timedelta:
    hours_str, minutes_str, seconds_str = string.split(":")
    return timedelta(
        hours=float(hours_str), minutes=float(minutes_str), seconds=float(seconds_str)
    )


class DatabaseAccess:
    def __init__(self) -> None:
        self.connection = sqlite3.connect("db/ldb.db")
        self.cursor = self.connection.cursor()

    def close(self) -> None:
        """Commit and close database connection."""
        self.connection.commit()
        self.connection.close()

    def fetch_by_first_header(
        self, table: str, headers: Iterable[str]
    ) -> Dict[str, Dict[str, object]]:
        """
        Return a dict for the first header in each row
        consisting of the remaining headers and entries.
        """
        self.cursor.execute(f"SELECT {', '.join(headers)} FROM {table};")
        return {
            entries[0]: {
                header: entry for header, entry in zip(headers[1:], entries[1:])
            }
            for entries in self.cursor.fetchall()
        }

    def fetch_env_infos(self) -> Dict[str, int]:
        """Return env_info in ldb as dict of names and counts."""
        self.cursor.execute("SELECT * FROM env_info;")
        return {name: count for name, count in self.cursor.fetchall()}

    def fetch_new_bookings(
        self, columns: Iterable[str], threshold: int = 0
    ) -> List[Dict[str, str]]:
        """
        Return from booking_info in ldb a dict of columns
        for which charging_session_id is greater than threshold.
        """
        self.cursor.execute(
            f"SELECT {', '.join(columns)} FROM booking_info"
            f" WHERE charging_session_id > {threshold};"
        )
        return [
            {column: entry for column, entry in zip(columns, entries)}
            for entries in self.cursor.fetchall()
        ]


if __name__ == "__main__":
    access = DatabaseAccess()
    bookings = access.fetch_new_bookings(BOOKING_HEADERS)
    print(bookings)
    if bookings:
        print(bookings[-1]["charging_session_status"])
        print(parse_datetime(bookings[-1]["drop_date_time"]))
    access.close()
