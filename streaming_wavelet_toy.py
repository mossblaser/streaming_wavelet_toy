from typing import List, Iterator, cast

from textwrap import indent, dedent

import time

import json

import random

from argparse import ArgumentParser

from logging_lazy_lists import AccessLogger, LoggingLazyList, LiftedLLL

from ascii_diagrams import Appearance, draw_array, draw_connections

from vc2_wavelet_definitions import (
    WaveletFilters,
    LiftingStage,
    ANALYSIS_FILTERS,
    SYNTHESIS_FILTERS,
)


def construct_lifted_arrays(
    input_lll: LoggingLazyList[int],
    logger: AccessLogger,
    lifting_stages: List[LiftingStage],
    intermediate_name_prefix: str,
    final_name: str,
) -> List[LoggingLazyList[int]]:
    out: List[LoggingLazyList[int]] = []
    previous_array = input_lll
    for i, stage in enumerate(lifting_stages):
        name = (
            f"{intermediate_name_prefix}{i+1}"
            if i != len(lifting_stages) - 1
            else final_name
        )
        array = LiftedLLL(name, previous_array, stage, logger)
        out.append(array)
        previous_array = array
    return out


def construct_all_arrays(
    input_values: List[int], wavelet: WaveletFilters, logger: AccessLogger,
) -> List[LoggingLazyList[int]]:
    arrays = []
    arrays.append(LoggingLazyList("Encoder Input", input_values, logger))
    arrays.extend(
        construct_lifted_arrays(
            arrays[-1],
            logger,
            ANALYSIS_FILTERS[wavelet],
            "Encode Intermediate ",
            "Encode Out/Decode In",
        )
    )
    arrays.extend(
        construct_lifted_arrays(
            arrays[-1],
            logger,
            SYNTHESIS_FILTERS[wavelet],
            "Decode Intermediate ",
            "Decoder Output",
        )
    )

    return arrays


def access_like_chained_filters(
    arrays: List[LoggingLazyList[int]], wavelet: WaveletFilters,
) -> None:
    """
    Trigger computation of array values as if lifting stages were a series of
    chained FIR filters.
    """
    # XXX: Delays may be too long/short
    delays = [0]
    for stage in ANALYSIS_FILTERS[wavelet]:
        delays.append(delays[-1] + stage.L)
    for stage in SYNTHESIS_FILTERS[wavelet]:
        delays.append(delays[-1] + stage.L)

    for i in range(len(arrays[-1]) + max(delays)):
        for delay, array in zip(delays, arrays):
            if 0 <= i - delay < len(array):
                array[i - delay]


def access_on_demand_encode_then_decode(
    arrays: List[LoggingLazyList[int]], wavelet: WaveletFilters,
) -> None:
    """
    Compute analysis and synthesis separately, but computing intermediate
    values only as they're needed.
    """
    list(arrays[len(ANALYSIS_FILTERS[wavelet])])
    list(arrays[-1])


def access_on_demand(
    arrays: List[LoggingLazyList[int]], wavelet: WaveletFilters,
) -> None:
    """
    Compute output values triggering all other computations (including
    encoding) only when first needed.
    """
    list(arrays[-1])


def access_like_block_filter(
    arrays: List[LoggingLazyList[int]], wavelet: WaveletFilters,
) -> None:
    """
    Compute values one lifting step in its entirety at a time.
    """
    for array in arrays:
        list(array)


def generate_animation(
    arrays: List[LoggingLazyList[int]],
    logger: AccessLogger,
    start: int = 0,
    end: int = -1,
) -> Iterator[str]:
    """
    Display the animated access/computation pattern which was logged.
    """
    name_col_width = max(len(a.name) + 1 for a in arrays)

    for t in range(start, end if end >= 0 else logger.time + 2 - end):
        frame = "\033[2J\033[H"
        for array in arrays:
            joins: str

            for call_record in logger.call_log:
                if (
                    call_record.array_name == array.name
                    and call_record.start_time <= t <= (call_record.end_time or 0)
                ):
                    sources = [
                        access.index
                        for access in call_record.access_log
                        if access.start_time <= t
                    ]
                    joins = draw_connections(sources, call_record.index)
                    break
            else:
                joins = "\n\n"

            values = draw_array(
                [
                    None
                    if t < logger.first_access_time.get((array.name, i), -1)
                    else v
                    if isinstance(v, int)
                    else None
                    for i, v in enumerate(array.iter_current_values())
                ],
                [
                    Appearance.dashed_border
                    if t < logger.first_access_time.get((array.name, i), -1)
                    else Appearance.dashed_border
                    if (
                        t > logger.last_access_time.get((array.name, i), -1)
                        and array != arrays[-1]
                    )
                    else Appearance.solid_border
                    for i in range(len(array))
                ],
            )

            if array != arrays[0]:
                frame += (indent(joins, " " * name_col_width)) + "\n"

            top, mid, bot = values.splitlines()
            frame += (indent(top, " " * name_col_width)) + "\n"
            frame += ("{:<{}s}{}".format(array.name, name_col_width, mid)) + "\n"
            frame += (indent(bot, " " * name_col_width)) + "\n"

        frame += "\n"
        frame += "         _ _ _   Value not         =====   Value will\n"
        frame += "Key:    ;     ;  used for         |     |  be used in\n"
        frame += "         - - -   any future        =====   a future\n"
        frame += "                 computation               computation\n"

        yield frame


def display_animation(
    arrays: List[LoggingLazyList[int]],
    logger: AccessLogger,
    delay: float = 0.1,
    start: int = 0,
    end: int = -1,
) -> None:
    for frame in generate_animation(arrays, logger, start, end):
        print(frame)
        time.sleep(delay)


def generate_terminalizer_animation(
    arrays: List[LoggingLazyList[int]],
    logger: AccessLogger,
    delay: float = 0.1,
    start: int = 0,
    end: int = -1,
) -> None:
    first_frame = next(iter(generate_animation(arrays, logger, start, end)))
    lines = first_frame.splitlines()
    num_rows = len(lines) + 1
    num_cols = len(lines[0])

    print(
        dedent(
            f"""
            config:
              cols: {num_cols}
              rows: {num_rows}
              repeat: 0
              quality: 100
              frameDelay: auto
              maxIdleTime: 2000
              frameBox:
                type: null
                title: null
                style: []
              watermark:
                imagePath: null
              fontFamily: "Monaco, Lucida Console, Ubuntu Mono, Monospace"
              fontSize: 12
              theme:
                background: "#000000"
        """
        ).strip()
    )
    print("records:")
    for i, frame in enumerate(generate_animation(arrays, logger, start, end)):
        frame = frame.replace("\n", "\r\n")
        print(f" - delay: {int((delay if i != 0 else 0)*1000)}")
        print(f"   content: {json.dumps(frame)}")


def parse_wavelet(value: str) -> WaveletFilters:
    try:
        return WaveletFilters(int(value))
    except ValueError:
        try:
            return getattr(WaveletFilters, value)
        except AttributeError:
            raise ValueError(value)


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument(
        "--wavelet",
        "-w",
        default=WaveletFilters.le_gall_5_3.name,
        choices=(
            [str(f.value) for f in WaveletFilters] + [f.name for f in WaveletFilters]
        ),
        help="""
            Wavelet transform to animate. Default: %(default)s.
        """,
    )

    parser.add_argument(
        "--input",
        "-i",
        default="random",
        choices=["ascending", "random"],
        help="""
            Input values to use in animation. Default: %(default)s.
        """,
    )

    parser.add_argument(
        "--num-values",
        "-n",
        type=int,
        default=16,
        help="""
            Length of signal. Default: %(default)s.
        """,
    )

    parser.add_argument(
        "--delay",
        "-d",
        type=float,
        default=0.025,
        help="""
            Delay between animation frames (seconds). Default: %(default)s.
        """,
    )

    parser.add_argument(
        "--order",
        "-o",
        choices=["block", "chained", "lazy", "lazy_two_steps"],
        default="block",
        help="""
            Computation order. Default: %(default)s. 'block' = compute each stage
            in its entirety, one after the other. 'chained' = perform computations
            as if all lifting stages have been implemented as a chain of FIR
            filters. 'lazy' = compute values only when required to compute each
            output value in turn. 'lazy_two_steps' = like 'lazy' except computes
            all transform values, then all output values (i.e. separates encoding
            an decoding).
        """,
    )

    parser.add_argument(
        "--display",
        "-D",
        default="terminal",
        choices=["terminal", "terminalizer"],
        help="""
            Output display mode. Default: %(default)s. 'terminal' = play animation
            directly in the terminal. 'terminalizer' = output YAML file suitable
            for rendering by the 'terminalizer' GIF generation tool.
        """,
    )

    args = parser.parse_args()

    wavelet: WaveletFilters = parse_wavelet(args.wavelet)

    input_values: List[int]
    if args.input == "ascending":
        input_values = list(range(args.num_values))
    elif args.input == "random":
        input_values = [random.randrange(100) for _ in range(args.num_values)]
    else:
        raise NotImplementedError(args.input)

    logger = AccessLogger()
    arrays = construct_all_arrays(input_values, wavelet, logger)

    if args.order == "block":
        access_like_block_filter(arrays, wavelet)
    elif args.order == "chained":
        access_like_chained_filters(arrays, wavelet)
    elif args.order == "lazy":
        access_on_demand(arrays, wavelet)
    elif args.order == "lazy_two_steps":
        access_on_demand_encode_then_decode(arrays, wavelet)
    else:
        raise NotImplementedError(args.order)

    if args.display == "terminal":
        display_animation(arrays, logger, args.delay)
    elif args.display == "terminalizer":
        generate_terminalizer_animation(arrays, logger, args.delay)
    else:
        raise NotImplementedError(args.display)
