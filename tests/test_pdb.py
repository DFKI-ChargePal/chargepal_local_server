#!/usr/bin/env python3
import os
import shutil
from sqlmodel import Session, select
from chargepal_local_server import debug_sqlite_db
from chargepal_local_server.access_ldb import LDB
from chargepal_local_server.create_ldb_orders import create_sample_booking
from chargepal_local_server.create_pdb import create_default_db
from chargepal_local_server.pdb_interfaces import Cart, Robot, pdb_engine
from chargepal_local_server.update_pdb import copy_from_ldb, fetch_updated_bookings


def get_absolute_filepath(relative_filepath: str) -> str:
    return os.path.join(os.path.dirname(__file__), relative_filepath)


def test_database_consistency() -> None:
    env_infos = LDB.fetch_env_infos()
    robot_infos = debug_sqlite_db.select("robot_info")
    cart_infos = debug_sqlite_db.select("cart_info")
    robot_count = len(robot_infos)
    cart_count = len(cart_infos)
    assert (
        len(env_infos["robot_names"])
        == LDB.fetch_env_count("robot_names")
        == robot_count
    ), f"Inconsistent robot count in env_info ({env_infos['robot_names']}) and robot_info ({robot_infos})."
    assert (
        len(env_infos["cart_names"]) == LDB.fetch_env_count("cart_names") == cart_count
    ), f"Inconsistent cart count in env_info ({env_infos['cart_names']}) and cart_info ({cart_count})."
    with Session(pdb_engine) as session:
        robots = session.exec(select(Robot)).fetchall()
        carts = session.exec(select(Cart)).fetchall()
        assert (
            len(robots) == robot_count
        ), f"Robot count in pdb ({len(robots)}) does not match with ldb ({robot_count})."
        assert (
            len(carts) == cart_count
        ), f"Cart count in pdb ({len(carts)}) does not match with ldb ({cart_count})."
        robot_names_ldb = sorted(list(robot_info[0] for robot_info in robot_infos))
        robot_names_pdb = sorted(list(robot.name for robot in robots))
        cart_names_ldb = sorted(list(cart_info[0] for cart_info in cart_infos))
        cart_names_pdb = sorted(list(cart.name for cart in carts))
        assert set(robot_names_pdb) == set(
            robot_names_ldb
        ), f"Robot names in pdb ({robot_names_pdb}) does not match with ldb ({robot_names_ldb})."
        assert set(cart_names_pdb) == set(
            cart_names_ldb
        ), f"Cart names in pdb ({cart_names_pdb}) does not match with ldb ({cart_names_ldb})."


def test_pdb_update() -> None:
    shutil.copyfile(
        get_absolute_filepath("ldb_no_orders.db"),
        get_absolute_filepath("../src/chargepal_local_server/db/ldb.db"),
    )
    # Check fetching from empty ldb.
    create_default_db()
    copy_from_ldb()
    assert not fetch_updated_bookings()
    # Check fetching one new booking.
    create_sample_booking()
    assert not fetch_updated_bookings()
    copy_from_ldb()
    assert len(fetch_updated_bookings()) == 1
    assert not fetch_updated_bookings()
    # Check fetching one update and one new booking.
    debug_sqlite_db.update(
        "orders_in SET charging_session_status = 'finished' WHERE charging_session_id = 1"
    )
    create_sample_booking()
    copy_from_ldb()
    assert len(fetch_updated_bookings()) == 2


if __name__ == "__main__":
    test_database_consistency()
    test_pdb_update()
