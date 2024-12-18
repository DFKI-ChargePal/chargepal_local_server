#!/usr/bin/env python3
import sys
import time
from chargepal_local_server import debug_sqlite_db
from chargepal_local_server.create_ldb_orders import create_sample_booking


DEFAULT_OPERATION_TIME = 20.0
DEFAULT_LOOP_TIME = 10.0


def loop(operation_time: float, loop_time: float) -> None:
    while True:
        print("Create new booking.")
        create_sample_booking()
        print(f"Wait for {operation_time} seconds.")
        time.sleep(operation_time)
        print("Wait for database update by charger.")
        while True:
            status = debug_sqlite_db.select("charging_session_status FROM orders_in")[-1][0]
            if status == "plugin_success":
                time.sleep(1.0)
                print("Finish charging vehicle.")
                debug_sqlite_db.update(
                    "orders_in SET charging_session_status = 'ready'"
                    " WHERE charging_session_status = 'plugin_success'"
                )
                break
        print(f"Wait for {loop_time} seconds.")
        time.sleep(loop_time)


if __name__ == "__main__":
    operation_time = DEFAULT_OPERATION_TIME
    loop_time = DEFAULT_LOOP_TIME
    if len(sys.argv) > 1 and sys.argv[1].isnumeric():
        operation_time = float(sys.argv[1])
        print(f"Using operation time: {operation_time}")
        if len(sys.argv) > 2 and sys.argv[2].isnumeric():
            loop_time = float(sys.argv[2])
            print(f"Using loop time: {loop_time}")
    loop(operation_time, loop_time)
