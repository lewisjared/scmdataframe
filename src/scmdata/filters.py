"""
Helpers for filtering data in :class:`scmdata.run.ScmRun`.

Based upon :mod:`pyam.utils`.
"""

import datetime
import re
import time
from typing import Any, Iterable, List, Optional, Union

import numpy as np
import pandas as pd

from scmdata._typing import MetadataValue

HIERARCHY_SEPARATOR = "|"


def is_in(vals: Iterable[Any], items: Iterable[Any]) -> np.ndarray:
    """
    Find elements of vals which are in items.

    Parameters
    ----------
    vals
        The list of values to check

    items
        The options used to determine whether each element of :obj:`vals` is in the
        desired subset or not

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array of the same length as :obj:`vals` where the element is ``True`` if the
        corresponding element of :obj:`vals` is in :obj:`items` and False otherwise
    """
    return np.array([v in items for v in vals])


def find_depth(
    meta_col: pd.Series,
    s: str,
    level: Union[int, str],
    separator: str = HIERARCHY_SEPARATOR,
) -> List[Any]:
    """
    Find all values which match given depth from a filter keyword.

    Parameters
    ----------
    meta_col
        Column in which to find values which match the given depth

    s
        Filter keyword, from which level should be applied

    level
        Depth of value to match as defined by the number of separator in the value name.
        If an int, the depth is matched exactly. If a str, then the depth can be matched
        as either "X-", for all levels up to level "X", or "X+", for all levels above
        level "X".

    separator
        The string used to separate levels in s. Defaults to a pipe ("|").

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array where ``True`` indicates a match

    Raises
    ------
    ValueError
        If :obj:`level` cannot be understood
    """
    # determine function for finding depth level
    if not isinstance(level, str):

        def test(x):
            return level == x

    elif level[-1] == "-":
        _level = int(level[:-1])

        def test(x):
            return _level >= x

    elif level[-1] == "+":
        _level = int(level[:-1])

        def test(x):
            return _level <= x

    else:
        raise ValueError(f"Unknown level type: {level}")

    # determine depth
    pipe = re.compile(re.escape(separator))
    regexp = str(s).replace("*", "")

    def apply_test(val):
        return test(len(pipe.findall(val.replace(regexp, ""))))

    return [m for m in meta_col.categories if apply_test(m)]


def pattern_match(  # pylint: disable=too-many-arguments,too-many-locals
    meta_col: pd.Index,
    values: Union[Iterable[MetadataValue], MetadataValue],
    level: Optional[MetadataValue] = None,
    regexp: bool = False,
    separator: str = HIERARCHY_SEPARATOR,
) -> np.ndarray:
    """
    Filter data by matching metadata columns to given patterns.

    Parameters
    ----------
    meta_col
        Column to perform filtering on

    values
        Values to match

    level
        Passed to :func:`find_depth`. For usage, see docstring of :func:`find_depth`.

    regexp
        If ``True``, match using regexp rather than our pseudo regexp syntax.

    has_nan
        If ``True``, convert all nan values in :obj:`meta_col` to empty string before
        applying filters. This means that "" and "*" will match rows with
        :class:`numpy.nan`. If ``False``, the conversion is not applied and so a search in
        a string column which contains :class:`numpy.nan` will result in a
        :class:`TypeError`.

    separator
        String used to separate the hierarchy levels in values. Defaults to '|'

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array where ``True`` indicates a match

    Raises
    ------
    TypeError
        Filtering is performed on a string metadata column which contains
        :class:`numpy.nan` and :obj:`has_nan` is ``False``
    """
    matches = np.array([False] * len(meta_col), dtype=bool)
    _values: Iterable[Any] = (
        [values]
        if not isinstance(values, Iterable) or isinstance(values, str)
        else values
    )

    for s in _values:
        comparison_value: str | float = s
        if isinstance(s, str) and s == "":
            comparison_value = np.nan

        use_string_comparison = isinstance(comparison_value, str) or (
            not np.isnan(comparison_value)
            and pd.api.types.is_string_dtype(meta_col.categories.dtype)
        )

        if use_string_comparison:
            if not regexp and comparison_value == "*" and level is None:
                matches |= True
            else:
                _regexp = (
                    str(s)
                    .replace("|", "\\|")
                    .replace(".", r"\.")  # `.` has to be replaced before `*`
                    .replace("*", ".*")
                    .replace("+", r"\+")
                    .replace("(", r"\(")
                    .replace(")", r"\)")
                    .replace("$", "\\$")
                    .replace("^", "\\^")
                ) + "$"
                pattern = re.compile(_regexp if not regexp else str(comparison_value))

                subset = [m for m in meta_col.categories if pattern.match(str(m))]

                if level is not None:
                    depth = find_depth(
                        meta_col, str(comparison_value), level, separator=separator
                    )
                    subset = set(subset).intersection(set(depth))

                matches |= meta_col.isin(subset)
        else:
            s_float = float(comparison_value)
            if np.isnan(s_float):
                matches |= [
                    c == -1 for c in meta_col.codes
                ]  # nan's are missing from categoricals
            else:
                matches |= np.isclose(s_float, meta_col.astype(float))

    return matches


def years_match(
    data: Iterable[Any], years: Union[Iterable[int], np.ndarray, int]
) -> np.ndarray:
    """
    Match years in time columns for data filtering.

    Parameters
    ----------
    data
        Input data to perform filtering on

    years
        Years to match

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array where True indicates a match

    Raises
    ------
    TypeError
        If :obj:`years` is not :obj:`int` or list of :obj:`int`
    """
    years = [years] if isinstance(years, int) else years
    usable_int = (
        all(isinstance(y, (int, np.integer)) for y in years)
        if isinstance(years, Iterable)
        else isinstance(years, int)
    )

    if not usable_int:
        error_msg = "`year` can only be filtered with ints or lists of ints"
        raise TypeError(error_msg)
    return is_in(data, years)


def month_match(
    data: Iterable[Any], months: Union[Iterable[Union[str, int]], int, str]
) -> np.ndarray:
    """
    Match months in time columns for data filtering.

    Parameters
    ----------
    data
        Input data to perform filtering on

    months
        Months to match

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array where ``True`` indicates a match
    """
    return time_match(data, months, ["%b", "%B"], "tm_mon", "month")


def day_match(
    data: Iterable[Any], days: Union[List[str], List[int], int, str]
) -> np.ndarray:
    """
    Match days in time columns for data filtering.

    Parameters
    ----------
    data
        Input data to perform filtering on

    days
        Days to match

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array where ``True`` indicates a match
    """
    return time_match(data, days, ["%a", "%A"], "tm_wday", "day")


def hour_match(data: Iterable[Any], hours: Union[Iterable[int], int]) -> np.ndarray:
    """
    Match hours in time columns for data filtering.

    Parameters
    ----------
    data
        Input data to perform filtering on

    hours
        Hours to match

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array where ``True`` indicates a match
    """
    hours_list = [hours] if isinstance(hours, int) else hours
    return is_in(data, hours_list)


def time_match(
    data: Iterable[Any],
    times: Union[Iterable[Union[str, int]], int, str],
    conv_codes: List[str],
    strptime_attr: str,
    name: str,
) -> np.ndarray:
    """
    Match times by applying conversion codes to filtering list.

    Parameters
    ----------
    data
        Input data to perform filtering on

    times
        Times to match

    conv_codes
        If :obj:`times` contains strings, conversion codes to try passing to
        :func:`time.strptime` to convert :obj:`times` to :class:`datetime.datetime`

    strptime_attr
        If :obj:`times` contains strings, the :class:`datetime.datetime` attribute to
        finalize the conversion of strings to integers

    name
        Name of the part of a datetime to extract, used to produce useful error
        messages.

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array where ``True`` indicates a match

    Raises
    ------
    ValueError
        If input times cannot be converted understood or if input strings do not lead to
        increasing integers (i.e. "Nov-Feb" will not work, one must use ["Nov-Dec",
        "Jan-Feb"] instead)
    """
    times_list: List[Union[int, str]] = (
        [times] if isinstance(times, (int, str)) else times
    )

    def conv_strs(strs_to_convert, conv_codes, name):
        res = None
        for conv_code in conv_codes:
            try:
                res = [
                    getattr(time.strptime(t, conv_code), strptime_attr)
                    for t in strs_to_convert
                ]
                break
            except ValueError:
                continue

        if res is None:
            error_msg = f"Could not convert {name} '{strs_to_convert}' to integer"
            raise ValueError(error_msg)
        return res

    if isinstance(times_list[0], str):
        to_delete = []
        to_append: List[Any] = []
        for i, timeset in enumerate(times_list):
            # ignore type as already established we're looking at strings
            if "-" in timeset:  # type: ignore
                ints = conv_strs(timeset.split("-"), conv_codes, name)  # type: ignore
                if ints[0] > ints[1]:
                    error_msg = (
                        "string ranges must lead to increasing integer ranges,"
                        f" {timeset} becomes {ints}"
                    )
                    raise ValueError(error_msg)

                # + 1 to include last month
                to_append += [j for j in range(ints[0], ints[1] + 1)]
                to_delete.append(i)

        for i in to_delete:
            del times_list[i]

        times_list = conv_strs(times_list, conv_codes, name)
        times_list += to_append

    return is_in(data, times_list)


def datetime_match(
    data: Iterable[Any], dts: Union[Iterable[datetime.datetime], datetime.datetime, str]
) -> np.ndarray:
    """
    Match datetimes in time columns for data filtering.

    Parameters
    ----------
    data
        Input data to perform filtering on

    dts
        Datetimes to use for filtering

    Returns
    -------
    :class:`numpy.ndarray` of :obj:`bool`
        Array where ``True`` indicates a match

    Raises
    ------
    TypeError
        :obj:`dts` contains :obj:`int`
    """
    dts = [dts] if isinstance(dts, datetime.datetime) else dts
    if isinstance(dts, int) or any([isinstance(d, int) for d in dts]):
        error_msg = "`time` can only be filtered with datetimes or lists of datetimes"
        raise TypeError(error_msg)
    return is_in(data, dts)
