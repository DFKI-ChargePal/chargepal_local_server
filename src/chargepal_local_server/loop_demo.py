#!/usr/bin/env python3
import debug_ldb
import time
from create_ldb_orders import create_sample_booking


OPERATION_TIME = 20.0
LOOP_TIME = 30.0


def loop() -> None:
    while True:
        create_sample_booking()
        time.sleep(OPERATION_TIME)
        while True:
            status = debug_ldb.select("charging_session_status FROM orders_in")[-1][0]
            if status == "plugin_success":
                debug_ldb.update(
                    "orders_in SET charging_session_status = 'finished'"
                    " WHERE charging_session_status = 'plugin_success'"
                )
                break
        time.sleep(LOOP_TIME)


if __name__ == "__main__":
    loop()
