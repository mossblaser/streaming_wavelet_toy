r"""
:py:class:`LoggingLazyList`\s are list like objects whose entries are computed
on first access (lazy) and accesses are logged by a :py:class:`AccessLogger`.
In this way, the sequence of computations and data flows which led to each
array value being computed can be tracked.
"""

from typing import (
    Optional,
    List,
    Tuple,
    MutableMapping,
    Iterator,
    Iterable,
    NamedTuple,
    TypeVar,
    Generic,
    Union,
)

from dataclasses import dataclass, field

from contextlib import contextmanager

from vc2_wavelet_definitions import LiftingStage


@dataclass
class AccessRecord:
    array_name: str
    index: int

    start_time: int
    end_time: Optional[int] = None


@dataclass
class CallRecord:
    array_name: str
    index: int

    start_time: int
    end_time: Optional[int] = None

    access_log: List[AccessRecord] = field(default_factory=list)


class AccessLogger:

    _time: int
    """Current timestamp."""

    _call_stack: List[CallRecord]
    """
    For each level in the call stack, the list of (array_name, index) tuples
    accessed during the call.
    """

    call_log: List[CallRecord]
    """
    Complete list of calls, ordered by start time.
    """

    first_access_time: MutableMapping[Tuple[str, int], int]
    last_access_time: MutableMapping[Tuple[str, int], int]
    """
    For each array index, the time at which it was first and last accessed.
    These times record when the access finished.
    """

    def __init__(self) -> None:
        self._time = 0
        self._call_stack = []
        self.call_log = []
        self.first_access_time = {}
        self.last_access_time = {}

    @property
    def time(self) -> int:
        """
        Get the current timestamp.
        
        (Time advances by one step every time this value is accessed.)
        """
        self._time += 1
        return self._time

    @contextmanager
    def new_context(self, array_name: str, index: int) -> Iterator[None]:
        """
        Context manager in which tracks the process of computing a value of an
        array.
        
        Takes the array name and index corresponding to the value which is
        being computed.
        """
        call_record = CallRecord(array_name, index, self.time)
        self._call_stack.append(call_record)
        self.call_log.append(call_record)

        try:
            yield
        finally:
            assert self._call_stack.pop(-1) == call_record
            call_record.end_time = self.time

    @contextmanager
    def log_access(self, array_name: str, index: int) -> Iterator[None]:
        """
        Context manager which tracks the process of accessing a value in
        another array.
        
        Takes the array name and index corresponding to the value which is
        being accessed.
        """
        access_record = AccessRecord(array_name, index, self.time)
        if self._call_stack:
            self._call_stack[-1].access_log.append(access_record)

        try:
            yield
        finally:
            t = self.time

            access_record.end_time = t

            if (array_name, index) not in self.first_access_time:
                self.first_access_time[(array_name, index)] = t

            self.last_access_time[(array_name, index)] = t


class Unknown(NamedTuple):
    """
    Sentinel type representing an as-yet uncomputed value within a
    LoggingLazyList.
    """


T = TypeVar("T")


class LoggingLazyList(Generic[T]):
    """
    Base class. implementers should implement the :py:meth:`compute_value`
    method. Alternatively, pre-populated lists may use this class directly.
    """

    name: str
    _values: List[Union[T, Unknown]]
    _logger: AccessLogger

    def __init__(
        self,
        name: str,
        length_or_values: Union[int, Iterable[Union[T, Unknown]]],
        logger: AccessLogger,
    ) -> None:
        self.name = name

        if isinstance(length_or_values, int):
            self._values = [Unknown()] * length_or_values
        else:
            self._values = list(length_or_values)

        self._logger = logger

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, index: int) -> T:
        with self._logger.log_access(self.name, index):
            existing_value = self._values[index]

            if isinstance(existing_value, Unknown):
                with self._logger.new_context(self.name, index):
                    value = self.compute_value(index)
                self._values[index] = value
                return value
            else:
                return existing_value

    def iter_current_values(self) -> Iterator[Union[T, Unknown]]:
        return iter(self._values)

    def __iter__(self) -> Iterator[T]:
        for i in range(len(self)):
            yield self[i]

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name} {repr(self._values)}>"

    def compute_value(self, index: int) -> T:
        raise NotImplementedError()


class LiftedLLL(LoggingLazyList[int]):
    """
    A list containing the result of applying a VC-2 lifting filter to another
    array's contents.
    """

    _source: LoggingLazyList[int]
    _lift: LiftingStage

    def __init__(
        self,
        name: str,
        source: LoggingLazyList[int],
        lift: LiftingStage,
        logger: AccessLogger,
    ) -> None:
        super().__init__(name, len(source), logger)
        self._source = source
        self._lift = lift

    def compute_value(self, index: int) -> int:
        lift_type, S, L, D, taps = self._lift

        even = (index % 2) == 0
        if lift_type.update_even == even:
            sum = 0
            for i in range(D, L + D):
                pos = index + (2 * i) - 1
                pos = min(pos, len(self._source) - (1 if lift_type.update_even else 2))
                pos = max(pos, 1 if lift_type.update_even else 0)
                sum += taps[i - D] * self._source[pos]
            if S > 0:
                sum += 1 << (S - 1)
            sum >>= S
            if lift_type.add:
                return self._source[index] + sum
            else:
                return self._source[index] - sum
        else:
            return self._source[index]
