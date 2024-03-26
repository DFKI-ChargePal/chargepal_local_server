"""
Planning Database functions to update entries
reading from local sqlite3 database (ldb)
"""

#!/usr/bin/env python3
from typing import Dict, Optional
from datetime import datetime, timedelta
import os
import re
import sqlite3
from sqlmodel import Session, insert, select, update
from chargepal_local_server.pdb_interfaces import (
    BookingInfo,
    CartInfo,
    RobotInfo,
    engine,
)


ldb_filepath = os.path.join(os.path.dirname(__file__), "db/ldb.db")
ldb_connection = sqlite3.connect(ldb_filepath)
ldb_cursor = ldb_connection.cursor()
last_booking_infos: Dict[int, BookingInfo] = {}


def is_sql_none(string: Optional[str]) -> bool:
    """Return whether string is None, including SQL representations."""
    return not string or string.upper() in ("NONE", "NULL")


def parse_sql_string(string: Optional[str]) -> Optional[str]:
    """Parse str from SQL string."""
    return None if is_sql_none(string) else string


def parse_datetime(string: Optional[str]) -> Optional[datetime]:
    """Parse datetime from SQL string."""
    if not string or not re.match(r"(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)$", string):
        return None

    return datetime.strptime(string, "%Y-%m-%d %H:%M:%S")


def parse_timedelta(string: Optional[str]) -> Optional[timedelta]:
    """Parse timedelta from SQL string."""
    if not string or not re.match(r"(\d+):(\d+):(\d+)$", string):
        return None

    hours_str, minutes_str, seconds_str = string.split(":")
    return timedelta(
        hours=float(hours_str),
        minutes=float(minutes_str),
        seconds=float(seconds_str),
    )


def copy_from_ldb() -> None:
    with Session(engine) as session:
        ldb_cursor.execute(
            """SELECT
            robot_name,
            robot_location,
            ongoing_action,
            previous_action,
            robot_charge,
            error_count FROM robot_info;"""
        )
        for (
            robot_name,
            robot_location,
            ongoing_action,
            previous_action,
            robot_charge,
            error_count,
        ) in ldb_cursor.fetchall():
            session.exec(
                update(RobotInfo)
                .values(
                    robot_location=robot_location,
                    ongoing_action=parse_sql_string(ongoing_action),
                    previous_action=parse_sql_string(previous_action),
                    robot_charge=float(robot_charge),
                    error_count=int(error_count),
                )
                .where(RobotInfo.robot_name == robot_name)
            )

        ldb_cursor.execute(
            """SELECT
            cart_name,
            cart_location FROM cart_info;"""
        )
        for (
            cart_name,
            cart_location,
        ) in ldb_cursor.fetchall():
            session.exec(
                update(CartInfo)
                .values(
                    cart_location=cart_location,
                )
                .where(CartInfo.cart_name == cart_name)
            )

        ldb_cursor.execute(
            """SELECT
            charging_session_id,
            drop_location,
            plugintime_calculated,
            drop_date_time,
            pick_up_date_time,
            booking_date_time_dev,
            charging_session_status,
            last_change,
            Actual_plugintime_calculated,
            Actual_BEV_Drop_Time,
            Actual_BEV_Pickup_Time FROM orders_in;"""
        )
        for (
            charging_session_id,
            drop_location,
            plugintime_calculated,
            drop_date_time,
            pick_up_date_time,
            booking_date_time_dev,
            charging_session_status,
            last_change,
            actual_plugintime_calculated,
            actual_BEV_drop_time,
            actual_BEV_pickup_time,
        ) in ldb_cursor.fetchall():
            booking_id = int(charging_session_id)
            charging_session_status = charging_session_status
            last_change = parse_datetime(last_change)
            planned_BEV_drop_time = parse_datetime(drop_date_time)
            planned_BEV_location = drop_location
            planned_plugintime_calculated = timedelta(
                minutes=float(plugintime_calculated)
            )
            planned_BEV_pickup_time = parse_datetime(pick_up_date_time)
            actual_BEV_drop_time = parse_datetime(actual_BEV_drop_time)
            actual_BEV_location = drop_location  # TODO clarify actual vs. planned
            actual_plugintime_calculated = timedelta(
                minutes=(
                    0.0
                    if is_sql_none(actual_plugintime_calculated)
                    else float(actual_plugintime_calculated)
                )
            )
            actual_BEV_pickup_time = parse_datetime(actual_BEV_pickup_time)
            if session.exec(
                select(BookingInfo).where(BookingInfo.booking_id == charging_session_id)
            ).first():
                session.exec(
                    update(BookingInfo)
                    .values(
                        charging_session_status=charging_session_status,
                        last_change=last_change,
                        planned_BEV_drop_time=planned_BEV_drop_time,
                        planned_BEV_location=planned_BEV_location,
                        planned_plugintime_calculated=planned_plugintime_calculated,
                        planned_BEV_pickup_time=planned_BEV_pickup_time,
                        actual_BEV_drop_time=actual_BEV_drop_time,
                        actual_BEV_location=actual_BEV_location,
                        actual_plugintime_calculated=actual_plugintime_calculated,
                        actual_BEV_pickup_time=actual_BEV_pickup_time,
                    )
                    .where(BookingInfo.booking_id == charging_session_id)
                )
            else:
                session.exec(
                    insert(BookingInfo).values(
                        booking_id=booking_id,
                        charging_session_status=charging_session_status,
                        last_change=last_change,
                        planned_BEV_drop_time=planned_BEV_drop_time,
                        planned_BEV_location=planned_BEV_location,
                        planned_plugintime_calculated=planned_plugintime_calculated,
                        planned_BEV_pickup_time=planned_BEV_pickup_time,
                        actual_BEV_drop_time=actual_BEV_drop_time,
                        actual_BEV_location=actual_BEV_location,
                        actual_plugintime_calculated=actual_plugintime_calculated,
                        actual_BEV_pickup_time=actual_BEV_pickup_time,
                        booking_time=parse_datetime(booking_date_time_dev),
                    )
                )

        session.commit()


def fetch_updated_booking_infos() -> Dict[int, BookingInfo]:
    updated_booking_infos: Dict[int, BookingInfo] = {}
    with Session(engine) as session:
        booking_infos = session.exec(select(BookingInfo)).fetchall()
        for booking_info in booking_infos:
            booking_id = booking_info.booking_id
            if (
                booking_info.booking_id not in last_booking_infos.keys()
                or booking_info != last_booking_infos[booking_id]
            ):
                last_booking_infos[booking_id] = booking_info
                updated_booking_infos[booking_id] = booking_info
    return updated_booking_infos


if __name__ == "__main__":
    copy_from_ldb()
