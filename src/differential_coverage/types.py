from collections.abc import Callable, Iterable
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, TypeVar
from statistics import mean, median

if TYPE_CHECKING:
    from differential_coverage.approach_data import ApproachData


class SupportsLessThan(Protocol):
    """Any type with __lt__ (used as set elements / dict keys that need ordering)."""

    def __lt__(self, other: Any, /) -> bool: ...


EdgeId = TypeVar("EdgeId", bound=SupportsLessThan)
TrialId = TypeVar("TrialId", bound=SupportsLessThan)
ApproachId = TypeVar("ApproachId", bound=SupportsLessThan)


class ValueReducer(Enum):
    MEDIAN = (median,)
    MIN = (min,)
    MAX = (max,)
    AVERAGE = (mean,)

    # tuples are a hack to make the enum members members instead of functions
    def reduce(self, values: Iterable[float]) -> float:
        fn: Callable[[Iterable[float]], float] = self.value[0]
        return fn(values)


class CollectionReducer(Enum):
    UNION = "union"
    INTERSECTION = "intersection"

    def reduce(
        self, approach_data: "ApproachData[TrialId, EdgeId]"
    ) -> frozenset[EdgeId]:
        match self:
            case CollectionReducer.UNION:
                return approach_data.edges_union
            case CollectionReducer.INTERSECTION:
                return approach_data.edges_intersection
            case _:
                raise ValueError(f"Invalid collection reducer: {self}")
