"""
Data tables describing the lifting wavelet filters implemented in the VC-2
video codec.
"""

from typing import NamedTuple, List, Mapping

from dataclasses import dataclass

from enum import IntEnum


class WaveletFilters(IntEnum):
    """Identifiers for each kind of wavelet"""

    deslauriers_dubuc_9_7 = 0
    le_gall_5_3 = 1
    deslauriers_dubuc_13_7 = 2
    haar_no_shift = 3
    haar_with_shift = 4  # NB: Same wavelet as haar_with_shift
    fidelity = 5
    daubechies_9_7 = 6


class LiftingFilterTypes(IntEnum):
    """Types of lifting filter."""

    even_add_odd = 1
    even_subtract_odd = 2
    odd_add_even = 3
    odd_subtract_even = 4

    @property
    def update_even(self) -> bool:
        return self in (
            LiftingFilterTypes.even_add_odd,
            LiftingFilterTypes.even_subtract_odd,
        )

    @property
    def add(self) -> bool:
        return self in (
            LiftingFilterTypes.even_add_odd,
            LiftingFilterTypes.odd_add_even,
        )


class LiftingStage(NamedTuple):
    lift_type: LiftingFilterTypes
    S: int  # Right shift to scale filter output values
    L: int  # Length of 'taps'
    D: int  # Filter delay
    taps: List[int]  # Filter taps

    def with_inverted_lift_type(self) -> "LiftingStage":
        """Return the inverse of this lifting operation."""
        return LiftingStage(
            {
                LiftingFilterTypes(1): LiftingFilterTypes(2),
                LiftingFilterTypes(2): LiftingFilterTypes(1),
                LiftingFilterTypes(3): LiftingFilterTypes(4),
                LiftingFilterTypes(4): LiftingFilterTypes(3),
            }[self.lift_type],
            self.S,
            self.L,
            self.D,
            self.taps,
        )


SYNTHESIS_FILTERS: Mapping[WaveletFilters, List[LiftingStage]] = {
    WaveletFilters.deslauriers_dubuc_9_7: [
        LiftingStage(lift_type=LiftingFilterTypes(2), S=2, L=2, D=0, taps=[1, 1]),
        LiftingStage(
            lift_type=LiftingFilterTypes(3), S=4, L=4, D=-1, taps=[-1, 9, 9, -1]
        ),
    ],
    WaveletFilters.le_gall_5_3: [
        LiftingStage(lift_type=LiftingFilterTypes(2), S=2, L=2, D=0, taps=[1, 1]),
        LiftingStage(lift_type=LiftingFilterTypes(3), S=1, L=2, D=0, taps=[1, 1]),
    ],
    WaveletFilters.deslauriers_dubuc_13_7: [
        LiftingStage(
            lift_type=LiftingFilterTypes(2), S=5, L=4, D=-1, taps=[-1, 9, 9, -1]
        ),
        LiftingStage(
            lift_type=LiftingFilterTypes(3), S=4, L=4, D=-1, taps=[-1, 9, 9, -1]
        ),
    ],
    WaveletFilters.haar_no_shift: [
        LiftingStage(lift_type=LiftingFilterTypes(2), S=1, L=1, D=1, taps=[1]),
        LiftingStage(lift_type=LiftingFilterTypes(3), S=0, L=1, D=0, taps=[1]),
    ],
    WaveletFilters.haar_with_shift: [
        LiftingStage(lift_type=LiftingFilterTypes(2), S=1, L=1, D=1, taps=[1]),
        LiftingStage(lift_type=LiftingFilterTypes(3), S=0, L=1, D=0, taps=[1]),
    ],
    WaveletFilters.fidelity: [
        LiftingStage(
            lift_type=LiftingFilterTypes(3),
            S=8,
            L=8,
            D=-3,
            taps=[-2, -10, -25, 81, 81, -25, 10, -2],
        ),
        LiftingStage(
            lift_type=LiftingFilterTypes(2),
            S=8,
            L=8,
            D=-3,
            taps=[-8, 21, -46, 161, 161, -46, 21, -8],
        ),
    ],
    WaveletFilters.daubechies_9_7: [
        LiftingStage(
            lift_type=LiftingFilterTypes(2), S=12, L=2, D=0, taps=[1817, 1817]
        ),
        LiftingStage(
            lift_type=LiftingFilterTypes(4), S=12, L=2, D=0, taps=[3616, 3616]
        ),
        LiftingStage(lift_type=LiftingFilterTypes(1), S=12, L=2, D=0, taps=[217, 217]),
        LiftingStage(
            lift_type=LiftingFilterTypes(3), S=12, L=2, D=0, taps=[6497, 6497]
        ),
    ],
}
"""
VC-2's lifting wavelet (synthesis) filters, as defined in the VC-2 spec.
"""

ANALYSIS_FILTERS = {
    wavelet: [stage.with_inverted_lift_type() for stage in reversed(stages)]
    for wavelet, stages in SYNTHESIS_FILTERS.items()
}
"""
Equivalent lifting wavelet analysis filters.
"""
