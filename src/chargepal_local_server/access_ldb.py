#!/usr/bin/env python3
from typing import Dict, Iterable, List, Optional
from datetime import datetime, timedelta
import re
import sqlite3

ALL_COLUMNS = (
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
    if now is None:
        now = datetime.now()
    if weeks or days or hours or minutes or seconds:
        now += timedelta(
            weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds
        )
    return now.isoformat(sep=" ", timespec="seconds")


def get_datetime(string: str) -> datetime:
    match_result = re.match(r"(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)$", string)
    assert match_result, "Error: Invalid datetime format!"
    return datetime(*map(int, match_result.groups()))


def time_str(
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, seconds)


def fetch_new_bookings(
    columns: Iterable[str], threshold: int = 0
) -> List[Dict[str, str]]:
    """
    Return from booking_info in ldb a dict of columns
     for which charging_session_id is greater than threshold.
    """
    connection = sqlite3.connect("db/ldb.db")
    cursor = connection.cursor()

    cursor.execute(
        f"SELECT {', '.join(columns)} FROM booking_info"
        f" WHERE charging_session_id > {threshold};"
    )
    results: List[Dict[str, str]] = [
        {column: entry for column, entry in zip(columns, entries)}
        for entries in cursor.fetchall()
    ]

    connection.commit()
    connection.close()
    return results


if __name__ == "__main__":
    bookings = fetch_new_bookings(ALL_COLUMNS)
    print(bookings)
    if bookings:
        print(bookings[-1]["charging_session_status"])
        print(get_datetime(bookings[-1]["drop_date_time"]))
