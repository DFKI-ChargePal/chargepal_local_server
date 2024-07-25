#!/usr/bin/env python3
from datetime import datetime, timedelta
import os
import sqlite3


db_filepath = os.path.join(os.path.dirname(__file__), "db/ldb.db")


def create_sample_booking(
    drop_location: str = "021",
    charging_session_status: str = "checked_in",
) -> None:
    connection = sqlite3.connect(db_filepath)
    cursor = connection.cursor()
    cursor.execute("SELECT MAX(charging_session_id) FROM orders_in")
    results = cursor.fetchall()
    booking_id = int(results[0][0]) + 1 if results and results[0][0] else 1
    now = datetime.now()
    now_str = now.isoformat(sep=" ", timespec="seconds")
    booking_data = (
        str(booking_id),                                                    # charging_session_id TEXT
        "NULL",                                                             # app_id TEXT
        "2",                                                                # customer_id TEXT
        "5YJSA7H11FFP67457",                                                # VIN TEXT
        "11",                                                               # bev_chargePower_kW_AC_I TEXT
        "NULL",                                                             # bev_chargePower_kW_AC_II TEXT
        "TYP2",                                                             # bev_charge_Port_AC TEXT
        "250",                                                              # bev_fastcharge_power_DC_I TEXT
        "NULL",                                                             # bev_fastcharge_power_DC_II TEXT
        "CCS",                                                              # bev_fastcharge_port TEXT
        "LeftSide-Rear",                                                    # bev_Port_Location TEXT
        drop_location,                                                      # drop_location TEXT
        "AC",                                                               # BEV_slot_planned TEXT
        "195.87",                                                           # plugintime_calculated TEXT
        "80",                                                               # target_soc_pct TEXT
        "NULL",                                                             # current_BEV_slot_recond TEXT
        now_str,                                                            # drop_date_time TEXT
        (now + timedelta(hours=2)).isoformat(sep=" ", timespec="seconds"),  # pick_up_date_time TEXT
        "NULL",                                                             # arrival_timestamp TEXT
        now_str,                                                            # booking_date_time_dev TEXT
        charging_session_status,                                            # charging_session_status TEXT
        now_str,                                                            # last_change TEXT
        "NULL",                                                             # immediate_charge TEXT
        "20",                                                               # Actual_Drop_SOC TEXT
        "80",                                                               # Actual_Target_SOC TEXT
        "NULL",                                                             # Actual_plugintime_calculated TEXT
        now_str,                                                            # Actual_BEV_Drop_Time TEXT
        "NULL",                                                             # Actual_BEV_Pickup_Time TEXT
    )

    cursor.execute(
        "INSERT INTO orders_in VALUES"
        " (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        booking_data,
    )

    connection.commit()
    connection.close()


def create_table() -> bool:
    connection = sqlite3.connect(db_filepath)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = 'orders_in';"
    )
    if cursor.fetchall():
        return False

    cursor.execute(
        """
        CREATE TABLE orders_in (
            charging_session_id TEXT,
            app_id TEXT,
            customer_id TEXT,
            VIN TEXT,
            bev_chargePower_kW_AC_I TEXT,
            bev_chargePower_kW_AC_II TEXT,
            bev_charge_Port_AC TEXT,
            bev_fastcharge_power_DC_I TEXT,
            bev_fastcharge_power_DC_II TEXT,
            bev_fastcharge_port TEXT,
            bev_Port_Location TEXT,
            drop_location TEXT,
            BEV_slot_planned TEXT,
            plugintime_calculated TEXT,
            target_soc_pct TEXT,
            current_BEV_slot_recond TEXT,
            drop_date_time TEXT,
            pick_up_date_time TEXT,
            arrival_timestamp TEXT,
            booking_date_time_dev TEXT,
            charging_session_status TEXT,
            last_change TEXT,
            immediate_charge TEXT,
            Actual_Drop_SOC TEXT,
            Actual_Target_SOC TEXT,
            Actual_plugintime_calculated TEXT,
            Actual_BEV_Drop_Time TEXT,
            Actual_BEV_Pickup_Time TEXT
        )
        """
    )

    connection.commit()
    connection.close()
    return True


if __name__ == "__main__":
    if create_table():
        print("Table 'orders_in' created.")
    else:
        create_sample_booking()
        print("New booking created into table 'orders_in'.")
