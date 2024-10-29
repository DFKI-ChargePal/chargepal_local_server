#!/usr/bin/env python3
from typing import Dict, Iterable, List, Optional


def enumerate_names(prefix: str, count: int) -> List[str]:
    """
    Return list of count names consisting of prefix and enumerated postfix starting at 1.
    """
    return [f"{prefix}{number}" for number in range(1, count + 1)]


def get_names(
    prefix: str, names: Optional[Iterable[str]], count: Optional[int]
) -> List[str]:
    """
    Return names if given, else enumerate_names() with prefix and count if given, else [].
    """
    return names if names else enumerate_names(prefix, count) if count else []


class Config:
    """Initial ChargePal scenario configuration of robots, cart, and stations."""

    def __init__(
        self,
        *,
        ADS_count: Optional[int] = None,
        BCS_count: Optional[int] = None,
        robot_count: Optional[int] = None,
        cart_count: Optional[int] = None,
        ADS_names: Optional[Iterable[str]] = None,
        BCS_names: Optional[Iterable[str]] = None,
        BWS_names: Optional[Iterable[str]] = None,
        robot_locations: Dict[str, str] = None,
        cart_locations: Dict[str, str] = None,
    ) -> None:
        """
        - Specify adapter stations with ADS_names,
        or use ADS_count for default names starting with "ADS_".
        - Specify battery charging stations with BCS_names,
        or use BCS_count for default names starting with "BCS_".
        - Specify battery waiting stations with BWS_names,
        or their names start with "BWS_" by default and their count is the number of carts.
        - Robot base stations have default names starting with "RBS_".
        - Specify robot names and initial locations with robot_locations,
        or their names start with "ChargePal" by default and their count is robot_count if given, else 0.
        Robot default locations are their robot base stations starting with "RBS_".
        - Specify cart names and initial locations with cart_locations,
        or their names start with "BAT_" by default and their count is cart_count if given, else 0.
        Cart default locations are battery waiting stations starting with "BWS_".
        """

        self.ADS_names = get_names("ADS_", ADS_names, ADS_count)
        self.BCS_names = get_names("BCS_", BCS_names, BCS_count)
        self.BWS_names = get_names(
            "BWS_",
            BWS_names,
            len(cart_locations) if cart_locations else cart_count if cart_count else 0,
        )
        self.RBS_names = enumerate_names(
            "RBS_",
            (
                len(robot_locations)
                if robot_locations
                else robot_count
                if robot_count
                else 0
            ),
        )
        self.robot_locations = (
            robot_locations
            if robot_locations
            else {
                robot: station
                for robot, station in zip(
                    enumerate_names("ChargePal", len(self.RBS_names)), self.BWS_names
                )
            }
        )
        self.cart_locations = (
            cart_locations
            if cart_locations
            else {
                cart: station
                for cart, station in zip(
                    enumerate_names("BAT_", len(self.BWS_names)), self.BWS_names
                )
            }
        )
        all_station_names = (
            self.ADS_names + self.BCS_names + self.BWS_names + self.RBS_names
        )
        for robot, station in self.robot_locations.items():
            assert (
                station in all_station_names
            ), f"Invalid location {station} for {robot}."
        for cart, station in self.cart_locations.items():
            assert (
                station in all_station_names
            ), f"Invalid location {station} for {cart}."

    def __repr__(self) -> str:
        return f"{self.counts_str}\n" + str(self.locations)

    @property
    def ADS_count(self) -> int:
        return len(self.ADS_names)

    @property
    def BCS_count(self) -> int:
        return len(self.BCS_names)

    @property
    def BWS_count(self) -> int:
        return len(self.BWS_names)

    @property
    def RBS_count(self) -> int:
        return len(self.RBS_names)

    @property
    def robot_count(self) -> int:
        return len(self.robot_locations)

    @property
    def cart_count(self) -> int:
        return len(self.cart_locations)

    @property
    def counts_str(self) -> str:
        return (
            f"ADS: {self.ADS_count}, BCS: {self.BCS_count},"
            f" BWS: {self.BWS_count}, RBS: {self.RBS_count},"
            f" robots: {self.robot_count}, carts: {self.cart_count}"
        )

    @property
    def locations(self) -> Dict[str, str]:
        return {**self.robot_locations, **self.cart_locations}


CONFIG_ALL_ONE = Config(
    ADS_count=1,
    BCS_count=1,
    robot_count=1,
    cart_count=1,
)


CONFIG_DEFAULT = Config(
    ADS_count=2,
    BCS_count=2,
    cart_count=3,
    robot_locations={"ChargePal1": "RBS_1", "ChargePal2": "RBS_2"},
)


if __name__ == "__main__":
    print("- CONFIG_ALL_ONE:")
    print(CONFIG_ALL_ONE)
    print("- CONFIG_DEFAULT:")
    print(CONFIG_DEFAULT)
