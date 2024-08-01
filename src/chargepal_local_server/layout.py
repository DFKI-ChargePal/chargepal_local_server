"""Helper script to define parking area layout details"""

from functools import lru_cache
from sqlmodel import Session, select
from chargepal_local_server.pdb_interfaces import Distance, pdb_engine

# Use reference layout from simulation for now, see:
# https://git.ni.dfki.de/chargepal/chargepal_griddly/-/blob/main/chargepal_griddly/chargepal_full_domain/chargepal_full_domain.yaml
# Update database entries with real parking area layout when available.
#
# Legend:
# - a = adapter station
# - b = battery charging station
# - p = parking slot
# - r = robot base station
# - w = wall
#
# .b.b...r.
# .........
# ...awa...
# ...pwp...
# ....w....
# ...awa...
# ...pwp...
# .........
# .........


CELL_SIZE = 2.5
MAX_DISTANCE = 16 * CELL_SIZE
POSITIONS = {
    "ADS_1": (3, 2),
    "ADS_2": (5, 2),
    "ADS_3": (3, 5),
    "ADS_4": (5, 5),
    "BCS_1": (1, 0),
    "BCS_2": (3, 0),
    "BWS_1": (1, 0),
    "BWS_2": (3, 0),
    "RBS_1": (7, 0),
}


class Layout:
    @staticmethod
    def calculate_manhattan_distance(x1: int, y1: int, x2: int, y2: int) -> int:
        """Return Manhattan distance between (x1, y1) and (x2, y2)."""
        return (abs(x2 - x1) + abs(y2 - y1)) * CELL_SIZE

    @classmethod
    def calculate_distance(cls, source: str, target: str) -> float:
        """Return distance from source to target, calculated from POSITIONS."""
        if source in POSITIONS.keys() and target in POSITIONS.keys():
            distance = cls.calculate_manhattan_distance(
                *POSITIONS[source], *POSITIONS[target]
            )
            return distance
        return MAX_DISTANCE

    @classmethod
    @lru_cache
    def get_distance(cls, source: str, target: str) -> float:
        """Return distance from source to target, retrieced from pdb."""
        with Session(pdb_engine) as session:
            result = session.exec(
                select(Distance).where(Distance.start == source)
            ).first()
            if result is not None and hasattr(result, target):
                return getattr(result, target)
        return MAX_DISTANCE
