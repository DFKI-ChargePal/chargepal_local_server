"""Planning Database interfaces using SQLModel library"""

from typing import Optional
from datetime import datetime, timedelta
import os
from sqlmodel import Field, SQLModel, create_engine


def to_str(obj: object) -> str:
    return (
        str(obj)
        if obj is None or isinstance(obj, (bool, float, int, str))
        else f"'{obj}'"
    )


class RobotInfo(SQLModel, table=True):
    robot_name: str = Field(primary_key=True)
    robot_location: str
    current_job_id: Optional[int]
    current_job: Optional[str]
    ongoing_action: Optional[str]
    previous_action: Optional[str]
    cart_on_robot: Optional[str]
    pending_job_id: Optional[int]
    robot_charge: float
    available: bool
    error_count: int


class CartInfo(SQLModel, table=True):
    cart_name: str = Field(primary_key=True)
    cart_location: str
    booking_id: Optional[int]
    plugged: Optional[str]
    action_state: Optional[str]
    mode_response: Optional[str]
    state_of_charge: Optional[str]
    status_flag: Optional[str]
    charger_ok: bool
    charger_state: Optional[str]
    charger_error: bool
    balancing_request: bool
    cart_charge: float
    available: bool
    error_count: int


class StationInfo(SQLModel, table=True):
    station_name: str = Field(primary_key=True)
    station_pose: str
    reservation: Optional[int]
    available: bool


class Job(SQLModel, table=True):
    id: int = Field(primary_key=True)
    type: str
    state: str
    schedule: datetime
    deadline: Optional[datetime]
    booking_id: Optional[int]
    currently_assigned: bool
    robot_name: Optional[str]
    cart_name: Optional[str]
    source_station: Optional[str]
    target_station: Optional[str]
    start: Optional[datetime]
    end: Optional[datetime]

    def __str__(self) -> str:
        return (
            f"Job(id={to_str(self.id)}, type={to_str(self.type)}, state={to_str(self.state)},"
            f" schedule={to_str(self.schedule)}, deadline={to_str(self.deadline)},"
            f" booking_id={to_str(self.booking_id)}, assigned={to_str(self.currently_assigned)},"
            f" robot_name={to_str(self.robot_name)}, cart_name={to_str(self.cart_name)},"
            f" source_station={to_str(self.source_station)}, target_station={to_str(self.target_station)},"
            f" start={to_str(self.start)}, end={to_str(self.end)})"
        )

    def __eq__(self, other: "Job") -> bool:
        return (
            self.id == other.id
            and self.type == other.id
            and self.state == other.id
            and self.schedule == other.id
            and self.deadline == other.id
            and self.booking_id == other.id
            and self.currently_assigned == other.currently_assigned
            and self.robot_name == other.id
            and self.cart_name == other.id
            and self.source_station == other.id
            and self.target_station == other.id
            and self.start == other.id
            and self.end == other.id
        )


class BookingInfo(SQLModel, table=True):
    booking_id: int = Field(primary_key=True)
    charging_session_status: str
    last_change: datetime
    planned_BEV_drop_time: datetime
    planned_BEV_location: str
    planned_plugintime_calculated: timedelta
    planned_BEV_pickup_time: datetime
    actual_BEV_drop_time: datetime
    actual_BEV_location: str
    actual_plugintime_calculated: timedelta
    actual_BEV_pickup_time: Optional[datetime]
    booking_completion: Optional[datetime]
    booking_time: datetime

    def __eq__(self, other: "BookingInfo") -> bool:
        return (
            other.booking_id == self.booking_id
            and other.charging_session_status == self.charging_session_status
            and other.last_change == self.last_change
            and other.planned_BEV_drop_time == self.planned_BEV_drop_time
            and other.planned_BEV_location == self.planned_BEV_location
            and other.planned_plugintime_calculated
            == self.planned_plugintime_calculated
            and other.planned_BEV_pickup_time == self.planned_BEV_pickup_time
            and other.actual_BEV_drop_time == self.actual_BEV_drop_time
            and other.actual_BEV_location == self.actual_BEV_location
            and other.actual_plugintime_calculated == self.actual_plugintime_calculated
            and other.actual_BEV_pickup_time == self.actual_BEV_pickup_time
            and other.booking_time == self.booking_time
        )


pdb_filepath = os.path.join(os.path.dirname(__file__), "db/pdb.db")
engine = create_engine(f"sqlite:///{pdb_filepath}")
SQLModel.metadata.create_all(engine)
