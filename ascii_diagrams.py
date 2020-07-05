"""
Routines for drawing ASCII-art diagrams of arrays like so::

     _ _ _ _ _ _ _ _ _ ===== =====
    ; 97  ; 73  ; 33  | 79  | 45  |
    '- - -'- - -'- - -'====='=====
                   |     |     |
                   +-----+-----+
                         |
     ===== ===== ===== _ _ _ _ _ _
    | 97  |  8  | 33  |     ;     ;
    '====='====='====='- - -'- - -
"""

from typing import Sequence, Optional

from dataclasses import dataclass

from enum import Enum


@dataclass(frozen=True)
class DrawingOptions:
    box_width: int = 6


class Appearance(Enum):
    hidden = "hidden"
    no_border = "no_border"
    dashed_border = "dashed_border"
    solid_border = "solid_border"


def draw_array(
    values: Sequence[Optional[int]],
    appearances: Sequence[Appearance],
    opt: DrawingOptions = DrawingOptions(),
) -> str:
    top = ""
    middle = ""
    bottom = ""

    if values:
        for i, (value, appearance) in enumerate(zip(values, appearances)):
            if appearance == Appearance.hidden or appearance == Appearance.no_border:
                new_top = [" "] * opt.box_width
                new_bottom = [" "] * opt.box_width
            else:
                if appearance == Appearance.solid_border:
                    new_top = [" "] + (["="] * (opt.box_width - 1))
                    new_bottom = ["'"] + (["="] * (opt.box_width - 1))
                else:
                    new_top = [" "] + (["_"] * (opt.box_width - 1))
                    new_bottom = ["'"] + (["-"] * (opt.box_width - 1))
                if appearance == Appearance.dashed_border:
                    for j in range(2, opt.box_width, 2):
                        new_top[j] = " "
                        new_bottom[j] = " "
            top += "".join(new_top)
            bottom += "".join(new_bottom)

            last_appearence = appearances[i - 1] if i >= 1 else appearance
            middle += (
                "|"
                if (
                    last_appearence == Appearance.solid_border
                    or appearance == Appearance.solid_border
                )
                else (
                    ";"
                    if (
                        last_appearence == Appearance.dashed_border
                        or appearance == Appearance.dashed_border
                    )
                    else " "
                )
            )

            if value is not None and appearance != Appearance.hidden:
                middle += "{:^{}d}".format(value, opt.box_width - 1)
            else:
                middle += " " * (opt.box_width - 1)

        if appearance == Appearance.solid_border:
            middle += "|"
            bottom += "'"
        elif appearance == Appearance.dashed_border:
            middle += ";"
            bottom += "'"
        else:
            middle += " "
            bottom += " "

    return "\n".join((top.rstrip(), middle.rstrip(), bottom.rstrip()))


def draw_connections(
    sources: Sequence[int], dest: int, opt: DrawingOptions = DrawingOptions()
) -> str:
    lhs = opt.box_width // 2
    rhs = opt.box_width - lhs - 1

    if not sources:
        return "\n\n"

    lines = []

    sources = sorted(sources)
    line = ""
    for x in range(max(sources) + 1):
        if x in sources:
            line += (" " * lhs) + "|" + (" " * rhs)
        else:
            line += " " * opt.box_width

    lines.append(line.rstrip())

    leftmost = min(min(sources), dest)
    rightmost = max(max(sources), dest)

    line = ""
    for x in range(rightmost + 1):
        left_in = leftmost < x <= rightmost
        right_in = leftmost <= x < rightmost
        line += ("-" * lhs) if left_in else (" " * lhs)
        if x >= leftmost and x <= rightmost:
            line += "+" if x == dest or x in sources else "-"
        else:
            line += " "
        line += ("-" * rhs) if right_in else (" " * rhs)
    lines.append(line)

    line = (" " * (dest * opt.box_width)) + (" " * lhs) + "|"
    lines.append(line)

    return "\n".join(lines)
