from dataclasses import dataclass
from datetime import timedelta


@dataclass
class Event:
    time: timedelta

    @property
    def max_timestamp(self) -> timedelta:
        return self.time


@dataclass
class BookingEvent(Event):
    # Note: time is booking_time.
    booking_id: int
    planned_BEV_drop_time: timedelta
    planned_BEV_location: str
    planned_drop_SOC: float
    planned_plugintime_calculated: timedelta
    planned_BEV_pickup_time: timedelta

    @property
    def max_timestamp(self) -> timedelta:
        return self.planned_BEV_pickup_time


@dataclass
class CancelationEvent(Event):
    booking_id: int


@dataclass
class CarAppearanceEvent(Event):
    pass


@dataclass
class CheckInEvent(Event):
    # Note: time is actual_BEV_drop_time.
    booking_id: int
    actual_BEV_location: str
    actual_drop_SOC: float
    actual_plugintime_calculated: timedelta

    @property
    def max_timestamp(self) -> timedelta:
        return self.time + self.actual_plugintime_calculated


@dataclass
class CheckOutEvent(Event):
    # Note: time is actual_BEV_pickup_time
    booking_id: int
    actual_BEV_location: str
