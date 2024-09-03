#!/usr/bin/env python3
from datetime import datetime, timedelta
from chargepal_local_server.access_ldb import LDB, MySQLAccess


def create_sample_booking(
    drop_location: str = "ADS_1",
    charging_session_status: str = "checked_in",
) -> None:
    with LDB.get() as cursor:
        cursor.execute("SELECT MAX(charging_session_id) FROM orders_in")
        results = cursor.fetchall()
        booking_id = int(results[0][0]) + 1 if results and results[0][0] else 1
        now = datetime.now()
        now_str = now.isoformat(sep=" ", timespec="seconds")
        booking_data = (
            str(booking_id),                                                    # charging_session_id - int(11), not NULL
            "0",                                                                # app_id - double
            "2",                                                                # customer_id - double
            "5YJSA7H11FFP67457",                                                # VIN - varchar(255)
            "11",                                                               # bev_chargePower_kW_AC_I - varchar(255)
            "NULL",                                                             # bev_chargePower_kW_AC_II - varchar(255)
            "TYP2",                                                             # bev_charge_Port_AC - varchar(255)
            "250",                                                              # bev_fastcharge_power_DC_I - varchar(255)
            "NULL",                                                             # bev_fastcharge_power_DC_II - varchar(255)
            "CCS",                                                              # bev_fastcharge_port - varchar(255)
            "Left Side - Rear",                                                 # bev_Port_Location - enum('Left Side - Rear','Left Side - Front','Front - Middle','Right Side - Front','Right Side - Rear','Rear - Middle')
            drop_location,                                                      # drop_location - varchar(255)
            "AC",                                                               # BEV_slot_planned - varchar(255)
            "195.87",                                                           # plugintime_calculated - decimal(10,2)
            "80",                                                               # target_soc_pct - double
            "NULL",                                                             # current_BEV_slot_recond - varchar(255)
            now_str,                                                            # drop_date_time - datetime
            (now + timedelta(hours=2)).isoformat(sep=" ", timespec="seconds"),  # pick_up_date_time - datetime
            now_str,                                                            # arrival_timestamp - datetime
            now_str,                                                            # booking_date_time_dev - datetime
            charging_session_status,                                            # charging_session_status - enum('booked','checked_in','pending','charging_BEV','charging_Idle','ready','canceled','no_show'), not NULL
            now_str,                                                            # last_change - datetime
            False,                                                              # immediate_charge - bit(1)
            "20",                                                               # Actual_Drop_SOC - double
            "80",                                                               # Actual_Target_SOC - double
            "0.00",                                                             # Actual_plugintime_calculated - decimal(10,2)
            now_str,                                                            # Actual_BEV_Drop_Time - datetime
            now_str,                                                            # Actual_BEV_Pickup_Time - datetime
        )
        cursor.execute(f"INSERT INTO orders_in VALUES {booking_data}")


def create_table() -> bool:
    with LDB.get() as cursor:
        cursor.execute(
            "SHOW TABLES LIKE 'orders_in';"
            if MySQLAccess.is_configured()
            else "SELECT name FROM sqlite_master WHERE type='table' AND name = 'orders_in';"
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

    return True


if __name__ == "__main__":
    if create_table():
        print("Table 'orders_in' created.")
    else:
        create_sample_booking()
        print("New booking created into table 'orders_in'.")
