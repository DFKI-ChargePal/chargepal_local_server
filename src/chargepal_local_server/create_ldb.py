#!/usr/bin/env python3
from typing import List
from sqlmodel import Session, delete
from chargepal_local_server.ldb_interfaces import (
    Cart_info,
    Env_info,
    Robot_info,
    ldb_engine,
)


def create_robot_info(name: str, location: str) -> Robot_info:
    return Robot_info(
        name=name,
        robot_location=location,
        current_job_id=None,
        current_job=None,
        ongoing_action=None,
        previous_action=None,
        cart_on_robot=None,
        job_status=None,
        availability=True,
        robot_charge=0.0,
        error_count=0,
    )


def create_cart_info(name: str, location: str) -> Cart_info:
    return Cart_info(
        name=name,
        cart_location=location,
        robot_on_cart=None,
        plugged=False,
        action_state=None,
        error_count=0,
    )


def clear_db() -> None:
    """Clear all tables in the ldb."""
    with Session(ldb_engine) as session:
        for table in (Cart_info, Env_info, Robot_info):
            session.exec(delete(table))
        session.commit()


def add_env_info(session: Session, name: str, entries: List[str]) -> None:
    session.add(Env_info(name=name, value=f"{entries}", count=len(entries)))


def main(
    robots_count: int = 1, carts_count: int = 1, ads_count: int = 1, bcs_count: int = 1
):
    clear_db()
    robot_names: List[str] = []
    cart_names: List[str] = []
    rbs_names: List[str] = []
    bws_names: List[str] = []
    ads_names: List[str] = [f"ADS_{number}" for number in range(1, ads_count + 1)]
    bcs_names: List[str] = [f"BCS_{number}" for number in range(1, bcs_count + 1)]
    with Session(ldb_engine) as session:
        for number in range(1, robots_count + 1):
            robot_name = f"ChargePal{number}"
            rbs_name = f"RBS_{number}"
            robot_names.append(robot_name)
            rbs_names.append(rbs_name)
            session.add(create_robot_info(robot_name, rbs_name))
        for number in range(1, carts_count + 1):
            cart_name = f"BAT_{number}"
            bws_name = f"BWS_{number}"
            cart_names.append(cart_name)
            bws_names.append(bws_name)
            session.add(create_cart_info(cart_name, bws_name))
        add_env_info(session, "robot_names", robot_names)
        add_env_info(session, "cart_names", cart_names)
        add_env_info(session, "rbs_names", rbs_names)
        add_env_info(session, "bws_names", bws_names)
        add_env_info(session, "ads_names", ads_names)
        add_env_info(session, "bcs_names", bcs_names)
        session.commit()


if __name__ == "__main__":
    main()
