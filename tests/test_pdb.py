#!/usr/bin/env python3
import os
import shutil
from chargepal_local_server import create_ldb_orders, create_pdb, debug_ldb, update_pdb


def get_absolute_filepath(relative_filepath: str) -> str:
    return os.path.join(os.path.dirname(__file__), relative_filepath)


def test_pdb_update() -> None:
    shutil.copyfile(
        get_absolute_filepath("ldb_no_orders.db"),
        get_absolute_filepath("../src/chargepal_local_server/db/ldb.db"),
    )
    # Check fetching from empty ldb.
    create_pdb.reset_db()
    update_pdb.copy_from_ldb()
    assert not update_pdb.fetch_updated_booking_infos()
    # Check fetching one new booking.
    create_ldb_orders.create_sample_booking()
    assert not update_pdb.fetch_updated_booking_infos()
    update_pdb.copy_from_ldb()
    assert len(update_pdb.fetch_updated_booking_infos()) == 1
    assert not update_pdb.fetch_updated_booking_infos()
    # Check fetching one update and one new booking.
    debug_ldb.update(
        "orders_in SET charging_session_status = 'finished' WHERE charging_session_id = 1"
    )
    create_ldb_orders.create_sample_booking()
    update_pdb.copy_from_ldb()
    assert len(update_pdb.fetch_updated_booking_infos()) == 2


if __name__ == "__main__":
    test_pdb_update()
