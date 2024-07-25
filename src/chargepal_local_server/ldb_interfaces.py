"""Local server database interfaces using SQLModel library"""

from typing import Optional
import os
from sqlmodel import Field, SQLModel, create_engine


class Robot_info(SQLModel, table=True):
    name: str = Field(primary_key=True)
    robot_location: str
    current_job_id: Optional[int]
    current_job: Optional[str]
    ongoing_action: Optional[str]
    previous_action: Optional[str]
    cart_on_robot: Optional[str]
    job_status: Optional[str]
    availability: bool
    robot_charge: float
    error_count: int


class Cart_info(SQLModel, table=True):
    name: str = Field(primary_key=True)
    cart_location: str
    robot_on_cart: Optional[str]
    plugged: Optional[str]
    action_state: Optional[str]
    error_count: int


class Env_info(SQLModel, table=True):
    name: str = Field(primary_key=True)
    value: str
    count: int


ldb_filepath = os.path.join(os.path.dirname(__file__), "db/ldb.db")
ldb_engine = create_engine(f"sqlite:///{ldb_filepath}")
SQLModel.metadata.create_all(ldb_engine)
