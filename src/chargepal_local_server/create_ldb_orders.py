#!/usr/bin/env python3
from datetime import datetime, timedelta
import os
import sqlite3
import sys


def create_sample_booking(
    db_filepath: str = os.path.join(os.path.dirname(__file__), "db/ldb.db"),
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


def create_table(
    db_filepath: str = os.path.join(os.path.dirname(__file__), "db/ldb.db"),
    drop_existing_table: bool = False,
) -> None:
    connection = sqlite3.connect(db_filepath)
    cursor = connection.cursor()

    if drop_existing_table:
        cursor.execute("DROP TABLE orders_in;")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders_in (
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

    print("Inserting values into table orders_in.")
    create_sample_booking(db_filepath)


if __name__ == "__main__":
    if len(sys.argv) <= 2:
        create_table(drop_existing_table=bool(len(sys.argv) > 1 and sys.argv[1]))
    else:
        print(f"Usage: {os.path.basename(__file__)} [<drop previous orders_in table>]")
