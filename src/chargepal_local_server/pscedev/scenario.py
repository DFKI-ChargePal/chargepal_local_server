from typing import List, Optional
from dataclasses import dataclass
from datetime import timedelta
from chargepal_local_server.pscedev.config import Config
from chargepal_local_server.pscedev.interface import (
    BookingEvent,
    CarAppearanceEvent,
    CheckOutEvent,
    CheckInEvent,
    Event,
)


@dataclass
class Scenario:
    config: Config
    events: List[Event]

    @property
    def duration(self) -> timedelta:
        return max(event.max_timestamp for event in self.events)


def create_all_one_scenario(events: Optional[List[Event]] = None) -> Scenario:
    """Return new sceanrio instance with all entity counts being 1."""
    return Scenario(
        Config(
            ADS_count=1,
            BCS_count=1,
            robot_count=1,
            cart_count=1,
        ),
        events=events if events else [],
    )


def create_default_scenario(events: Optional[List[Event]] = None) -> Scenario:
    """Return new scenario instance with default entity counts."""
    return Scenario(
        Config(
            ADS_count=2,
            BCS_count=2,
            robot_count=2,
            cart_count=3,
        ),
        events=events if events else [],
    )


def load_scenario(filepath: str, name: str) -> Scenario:
    """Load scenario with name from filepath."""


def save_scenario(scenario: Scenario, filepath: str, name: str) -> None:
    """Save scenario into filepath as name."""


def immediately() -> timedelta:
    """Return a timedelta with zero duration."""
    return timedelta()


def seconds(count: int) -> timedelta:
    """Return a timedelta with count seconds."""
    return timedelta(seconds=count)


def minutes(count: int) -> timedelta:
    """Return a timedelta with count minutes."""
    return timedelta(minutes=count)


SCENARIO1 = create_all_one_scenario(
    [
        BookingEvent(
            immediately(),
            booking_id=1,
            planned_BEV_drop_time=immediately(),
            planned_BEV_location="ADS_1",
            planned_drop_SOC=0.2,
            planned_plugintime_calculated=minutes(1),
            planned_BEV_pickup_time=minutes(5),
        ),
        CarAppearanceEvent(immediately()),
        CheckInEvent(
            minutes(1),
            booking_id=1,
            actual_BEV_location="ADS_1",
            actual_drop_SOC=0.25,
            actual_plugintime_calculated=minutes(1),
        ),
        CheckOutEvent(
            minutes(3),
            booking_id=1,
            actual_BEV_location="ADS_1",
        ),
    ]
)

SCENARIO2 = Scenario(
    Config(
        ADS_count=1,
        BCS_count=1,
        robot_count=1,
        cart_count=2,
    ),
    events=[
        BookingEvent(
            immediately(),
            booking_id=1,
            planned_BEV_drop_time=immediately(),
            planned_BEV_location="ADS_1",
            planned_drop_SOC=0.2,
            planned_plugintime_calculated=minutes(3),
            planned_BEV_pickup_time=minutes(15),
        ),
        BookingEvent(
            immediately(),
            booking_id=2,
            planned_BEV_drop_time=immediately(),
            planned_BEV_location="ADS_1",
            planned_drop_SOC=0.9,
            planned_plugintime_calculated=minutes(1),
            planned_BEV_pickup_time=minutes(5),
        ),
        CarAppearanceEvent(immediately()),
        CheckInEvent(
            minutes(1),
            booking_id=2,
            actual_BEV_location="ADS_1",
            actual_drop_SOC=0.85,
            actual_plugintime_calculated=minutes(4),
        ),
        CarAppearanceEvent(minutes(5)),
        CheckOutEvent(
            minutes(6),
            booking_id=2,
            actual_BEV_location="ADS_1",
        ),
        CheckInEvent(
            minutes(7),
            booking_id=1,
            actual_BEV_location="ADS_1",
            actual_drop_SOC=0.25,
            actual_plugintime_calculated=minutes(12),
        ),
        CheckOutEvent(
            minutes(20),
            booking_id=1,
            actual_BEV_location="ADS_1",
        ),
    ],
)
