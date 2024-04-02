#!/usr/bin/env python3
from sqlmodel import Session, delete
from chargepal_local_server.pdb_interfaces import (
    Booking,
    CartInfo,
    Job,
    RobotInfo,
    StationInfo,
    engine,
)


def add_default_robots(session: Session, count: int, with_RBSs: bool = True) -> None:
    """Add count robots to session. If with_RBSs is true, also add an RBS per robot."""
    for number in range(1, count + 1):
        robot_name = f"ChargePal{number}"
        robot_location = f"RBS_{number}"
        session.add(
            RobotInfo(
                robot_name=robot_name,
                robot_location=robot_location,
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
        )
        if with_RBSs:
            session.add(
                StationInfo(
                    station_name=f"RBS_{number}",
                    station_pose="",
                    reservation=None,
                    available=False,
                )
            )


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
        session.add(
            CartInfo(
                cart_name=cart_name,
                cart_location=cart_location,
                booking_id=None,
                plugged=None,
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
        )
        if with_BWSs:
            session.add(
                StationInfo(
                    station_name=f"BWS_{number}",
                    station_pose="",
                    reservation=None,
                    available=False,
                )
            )
        if with_BCSs:
            session.add(
                StationInfo(
                    station_name=f"BCS_{number}",
                    station_pose="",
                    reservation=None,
                    available=True,
                )
            )


def add_default_ADSs(session: Session, count: int) -> None:
    """Add count ADSs to session."""
    for number in range(1, count + 1):
        session.add(
            StationInfo(
                station_name=f"ADS_{number}",
                station_pose="",
                reservation=None,
                available=True,
            )
        )


def add_default_BCSs(session: Session, count: int) -> None:
    """Add count BCSs to session."""
    for number in range(1, count + 1):
        session.add(
            StationInfo(
                station_name=f"BCS_{number}",
                station_pose="",
                reservation=None,
                available=True,
            )
        )


def reset_db() -> None:
    """Reset pdb by clearing all tables, then"""
    with Session(engine) as session:
        for info in (RobotInfo, CartInfo, StationInfo, Job, Booking):
            session.exec(delete(info))
        add_default_robots(session, 1)
        add_default_carts(session, 1, with_BCSs=True)
        add_default_ADSs(session, 1)
        session.commit()


if __name__ == "__main__":
    reset_db()
