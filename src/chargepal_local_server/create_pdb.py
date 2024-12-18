#!/usr/bin/env python3
from typing import List
from sqlmodel import Session, delete, update
from chargepal_local_server.access_ldb import LDB
from chargepal_local_server.layout import Layout
from chargepal_local_server.pdb_interfaces import (
    Booking,
    Cart,
    Distance,
    Job,
    Robot,
    Station,
    pdb_engine,
)
from chargepal_local_server.pscedev import Config


DATABASE_STATION_NAMES = list(Distance.__annotations__.keys())[1:]


def create_robot(name: str, location: str) -> Robot:
    return Robot(
        name=name,
        robot_location=location,
        current_job_id=None,
        current_job=None,
        ongoing_action=None,
        previous_action=None,
        cart_on_robot=None,
        pending_job_id=None,
        robot_charge=100.0,
        available=True,
        error_count=0,
    )


def create_cart(name: str, location: str) -> Cart:
    return Cart(
        name=name,
        cart_location=location,
        booking_id=None,
        plugged=False,
        action_state=None,
        mode_response=None,
        state_of_charge=None,
        status_flag=None,
        charger_ok=False,
        charger_state=None,
        charger_error=False,
        balancing_request=False,
        cart_charge=100.0,
        available=True,
        error_count=0,
    )


def create_station(name: str, available: bool = True) -> Station:
    return Station(
        station_name=name,
        station_pose="",
        reservation=None,
        available=available,
    )


def add_default_robots(session: Session, count: int, with_RBSs: bool = True) -> None:
    """Add count robots to session. If with_RBSs is true, also add an RBS per robot."""
    for number in range(1, count + 1):
        robot_name = f"ChargePal{number}"
        robot_location = f"RBS_{number}"
        session.add(create_robot(robot_name, robot_location))
        if with_RBSs:
            session.add(create_station(f"RBS_{number}", available=False))


def add_default_carts(
    session: Session, count: int, with_BWSs: bool = True, with_BCSs: bool = False
) -> None:
    """
    Add count carts to session. If with_BWSs is true, also add a BWS per cart.
    If with_BCSs is true, also add a BCS per cart.
    """
    for number in range(1, count + 1):
        cart_name = f"BAT_{number}"
        cart_location = f"BWS_{number}"
        session.add(create_cart(cart_name, cart_location))
        if with_BWSs:
            session.add(create_station(f"BWS_{number}", available=False))
        if with_BCSs:
            session.add(create_station(f"BCS_{number}"))


def add_default_ADSs(session: Session, count: int) -> None:
    """Add count ADSs to session."""
    for number in range(1, count + 1):
        session.add(create_station(f"ADS_{number}"))


def add_default_BCSs(session: Session, count: int) -> None:
    """Add count BCSs to session."""
    for number in range(1, count + 1):
        session.add(create_station(f"BCS_{number}"))


def clear_db() -> None:
    """Clear all tables in the pdb."""
    with Session(pdb_engine) as session:
        for table in (Robot, Cart, Distance, Station, Job, Booking):
            session.exec(delete(table))
        for station_name in DATABASE_STATION_NAMES:
            session.add(Distance(start=station_name))
        for source in DATABASE_STATION_NAMES:
            session.exec(
                update(Distance)
                .values(
                    **{
                        target: Layout.calculate_distance(source, target)
                        for target in DATABASE_STATION_NAMES
                    }
                )
                .where(Distance.start == source)
            )
        session.commit()


def create_default_db() -> None:
    """Clear pdb, then create one robot, cart, and station each."""
    clear_db()
    with Session(pdb_engine) as session:
        add_default_robots(session, 1)
        add_default_carts(session, 1)
        add_default_ADSs(session, 1)
        session.commit()


def create_from_ldb() -> None:
    """Clear pdb, then create robots, carts, and stations according to ldb."""
    clear_db()
    env_infos = LDB.fetch_env_infos()
    with Session(pdb_engine) as session:
        used_locations: List[str] = []
        robot_infos = LDB.fetch_by_first_header(
            "robot_info", ["name", "robot_location"]
        )
        for robot_name in env_infos["robot_names"]:
            robot_location: str = robot_infos[robot_name]["robot_location"]
            session.add(create_robot(robot_name, robot_location))
            used_locations.append(robot_location)
        cart_infos = LDB.fetch_by_first_header("cart_info", ["name", "cart_location"])
        for cart_name in env_infos["cart_names"]:
            cart_location: str = cart_infos[cart_name]["cart_location"]
            session.add(create_cart(cart_name, cart_location))
            used_locations.append(cart_location)
        for station_names in ["rbs_names", "bws_names", "ads_names", "bcs_names"]:
            for name in env_infos[station_names]:
                session.add(create_station(name, available=name not in used_locations))
        session.commit()


def initialize_db(config: Config) -> None:
    """Initialize pdb with config."""
    clear_db()
    with Session(pdb_engine) as session:
        for station_name in config.ADS_names + config.BCS_names:
            session.add(create_station(station_name))
        for station_name in config.BWS_names + config.RBS_names:
            session.add(create_station(station_name, available=False))
        for robot_name, robot_location in config.robot_locations.items():
            session.add(create_robot(robot_name, robot_location))
        for cart_name, cart_location in config.cart_locations.items():
            session.add(create_cart(cart_name, cart_location))
        session.commit()


if __name__ == "__main__":
    create_from_ldb()
