#!/usr/bin/env python3
import os
import sqlite3
import sys


def create_table(drop_previous_table: bool = False) -> None:
    connection = sqlite3.connect("db/ldb.db")
    cursor = connection.cursor()

    if drop_previous_table:
        print("Dropping previous table.")
        cursor.execute("DROP TABLE booking_info;")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_info (
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

    booking_data_1 = (
        "1079",
        "NULL",
        "2",
        "5YJSA7H11FFP67457",
        "NULL",
        "NULL",
        "NULL",
        "NULL",
        "NULL",
        "NULL",
        "NULL",
        "021",
        "021",
        "195.87",
        "80",
        "NULL",
        "2023-12-08 15:38:00",
        "2023-12-10 16:38:00",
        "NULL",
        "2023-12-08 15:38:00",
        "checked_in",
        "2023-12-08 17:00:39",
        "NULL",
        "20",
        "80",
        "NULL",
        "2023-12-08 17:00:00",
        "2023-12-10 16:38:00",
    )
    booking_data_2 = (
        "1085",
        "NULL",
        "2",
        "5YJSA7H11FFP67456",
        "11",
        "NULL",
        "TYP2",
        "250",
        "NULL",
        "CCS",
        "LeftSide-Rear",
        "NULL",
        "021",
        "254.95",
        "80",
        "NULL",
        "2024-01-13 11:59:00",
        "2024-01-13 12:59:00",
        "NULL",
        "2024-01-13 12:00:00",
        "booked",
        "NULL",
        "NULL",
        "NULL",
        "NULL",
        "NULL",
        "NULL",
        "NULL",
    )

    print("Inserting values into table booking_info.")
    cursor.execute(
        "INSERT INTO booking_info VALUES"
        " (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        booking_data_1,
    )

    connection.commit()
    connection.close()


if __name__ == "__main__":
    if len(sys.argv) <= 2:
        create_table(drop_previous_table=bool(len(sys.argv) > 1 and sys.argv[1]))
    else:
        print(f"Usage: {os.path.basename(__file__)} [<drop previous booking_info table>]")
