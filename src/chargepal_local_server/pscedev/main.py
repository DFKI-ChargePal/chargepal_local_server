from typing import Callable, Dict, List
from datetime import timedelta
from enum import IntEnum
from chargepal_local_server.pscedev.interface import (
    BookingEvent,
    CancelationEvent,
    CarAppearanceEvent,
    CheckInEvent,
    CheckOutEvent,
    Event,
)
from chargepal_local_server.pscedev.scenario import Scenario


class BookingStatus(IntEnum):
    BOOKED = 0
    CHECKED_IN = 1
    FULFILLED = 2
    COMPLETE = 3
    CANCELED = 4


class Monitoring:
    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        # Manage all timestamps of events which have not yet been reported.
        self.event_times = sorted(
            list(set(event.time for event in self.scenario.events))
        )
        self.current_time = timedelta()
        # Manage at which adapter stations there are cars currently.
        self.station_cars: Dict[str, bool] = {
            f"ADS_{number}": False for number in range(1, scenario.config.ADS_count + 1)
        }
        # Manage which adapter station is currently used for which booking.
        self.station_bookings: Dict[str, int] = {}
        # Manage statuses of bookings.
        self.bookings: Dict[int, BookingStatus] = {}

    def exists_event(self) -> bool:
        """Return whether there is at least one more event in the scenario."""
        return bool(self.event_times)

    def process_events(self, condition: Callable[[Event], bool]) -> List[Event]:
        """Process and return events which fulfill condition."""
        events: List[Event] = []
        for event in self.scenario.events:
            if condition(event):
                if isinstance(event, BookingEvent):
                    assert event.booking_id not in self.bookings.keys()
                    self.bookings[event.booking_id] = BookingStatus.BOOKED
                elif isinstance(event, CancelationEvent):
                    assert self.bookings[event.booking_id] in (
                        BookingStatus.BOOKED,
                        BookingStatus.CHECKED_IN,
                    )
                    self.bookings[event.booking_id] = BookingStatus.CANCELED
                elif isinstance(event, CarAppearanceEvent):
                    pass
                elif isinstance(event, CheckInEvent):
                    assert self.station_cars[event.actual_BEV_location]
                    assert self.bookings[event.booking_id] == BookingStatus.BOOKED
                    self.bookings[event.booking_id] = BookingStatus.CHECKED_IN
                    assert event.actual_BEV_location not in self.station_bookings.keys()
                    self.station_bookings[event.actual_BEV_location] = event.booking_id
                elif isinstance(event, CheckOutEvent):
                    assert self.station_cars[event.actual_BEV_location]
                    assert self.bookings[event.booking_id] == BookingStatus.FULFILLED
                    self.bookings[event.booking_id] = BookingStatus.COMPLETE
                    assert (
                        self.station_bookings[event.actual_BEV_location]
                        == event.booking_id
                    )
                    del self.station_bookings[event.actual_BEV_location]

                events.append(event)
        return events

    def get_events(self, time: timedelta) -> List[Event]:
        """
        Let time pass and return all events up to (including) the new timestamp.
        """

    def get_next_events(self) -> List[Event]:
        """
        Let time pass until a next event occurs.
        Return all events at the new timestamp.
        """
        for index, event_time in enumerate(self.event_times):
            if event_time >= self.current_time:
                # Collect events up to event_time.
                events = self.process_events(
                    lambda event: event.time in self.event_times
                    and event.time <= event_time
                )
                self.event_times[: index + 1] = []
                self.current_time = event_time
                return events
        return []

    def get_job_status(self, job_type: str, station_name: str) -> str:
        """
        Return job status for job_name.

        Note: Possible values are "Ongoing", "Success", "Failure", "Recovery".
        """
        if job_type == "BRING_CHARGER":
            assert self.station_cars[station_name]
            assert self.station_bookings[station_name]
        elif job_type == "RECHARGE_CHARGER":
            pass
        elif job_type == "STOW_CHARGER":
            pass
        elif job_type == "RECHARGE_SELF":
            pass
        return "Success"

    def update_car_at_ads(self, station_name: str, present: bool = True) -> None:
        assert station_name.startswith("ADS_")
        if self.station_cars[station_name] == present:
            print(f"Warning: Redundant car update for {station_name}.")
        else:
            self.station_cars[station_name] = present

    def update_car_charged(self, station_name: str) -> None:
        assert station_name.startswith("ADS_")
        booking_id = self.station_bookings[station_name]
        assert self.bookings[booking_id] == BookingStatus.CHECKED_IN
        self.bookings[booking_id] = BookingStatus.FULFILLED
