"""Planning Database interfaces using SQLModel library"""

from typing import Optional
from datetime import datetime, timedelta
import os
from sqlmodel import Field, SQLModel, create_engine


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


class JobInfo(SQLModel, table=True):
    job_id: int = Field(primary_key=True)
    job_type: str
    job_state: str
    schedule: datetime
    deadline: Optional[datetime]
    booking_id: int
    robot_name: Optional[str]
    cart_name: Optional[str]
    source_station: Optional[str]
    target_station: Optional[str]
    job_start: Optional[datetime]
    job_end: Optional[datetime]


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
