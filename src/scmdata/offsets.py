"""
Allow stepping through time using :mod:`xarray`'s offset functionality

Provides similar functionality to https://pandas.pydata.org/pandas-docs/stable/user_gui
de/timeseries.html#dateoffset-objects
"""
from typing import Iterable

import cftime
from xarray.coding import cftime_offsets
from xarray.coding.cftime_offsets import to_offset


def generate_range(
    start: cftime.datetime,
    end: cftime.datetime,
    offset: cftime_offsets.BaseCFTimeOffset,
    date_cls: cftime.datetime = cftime.DatetimeGregorian,
) -> Iterable[cftime.datetime]:
    """
    Generate a range of datetime objects between start and end, using offset to determine the steps

    The range will extend both ends of the span to the next valid timestep, see
    examples.

    Parameters
    ----------
    start: :class:`cftime.datetime`
        Starting datetime from which to generate the range (noting roll backward
        mentioned above and illustrated in the examples).

    end: :class:`cftime.datetime`
        Last datetime from which to generate the range (noting roll forward mentioned
        above and illustrated in the examples).

    offset:
        Offset object for determining the timesteps.

    date_cls : :class:`cftime.datetime`
            The time points will be returned as instances of ``date_cls``

    Yields
    ------
    :class:`cftime.datetime`
        Next datetime in the range (the exact class is specified by ``date_cls``)

    Raises
    ------
    ValueError
        Offset does not result in increasing :class:`cftime.datetime`'s

    Examples
    --------
    The range is extended at either end to the nearest timestep. In the example below,
    the first timestep is rolled back to 1st Jan 2001 whilst the last is extended to 1st
    Jan 2006.

    >>> import datetime as dt
    >>> from pprint import pprint
    >>> from scmdata.offsets import to_offset, generate_range
    >>> g = generate_range(
    ...     dt.datetime(2001, 4, 1),
    ...     dt.datetime(2005, 6, 3),
    ...     to_offset("AS"),
    ... )

    >>> pprint([d for d in g])
    [cftime.DatetimeGregorian(2001, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2002, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2003, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2004, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2005, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2006, 1, 1, 0, 0, 0, 0, has_year_zero=False)]

    In this example the first timestep is rolled back to 31st Dec 2000 whilst the last
    is extended to 31st Dec 2005.

    >>> g = generate_range(
    ...     dt.datetime(2001, 4, 1),
    ...     dt.datetime(2005, 6, 3),
    ...     to_offset("A"),
    ... )
    >>> pprint([d for d in g])
    [cftime.DatetimeGregorian(2000, 12, 31, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2001, 12, 31, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2002, 12, 31, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2003, 12, 31, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2004, 12, 31, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2005, 12, 31, 0, 0, 0, 0, has_year_zero=False)]

    In this example the first timestep is already on the offset so stays there, the last
    timestep is to 1st Sep 2005.

    >>> g = generate_range(
    ...     dt.datetime(2001, 4, 1),
    ...     dt.datetime(2005, 6, 3),
    ...     to_offset("QS"),
    ... )
    >>> pprint([d for d in g])
    [cftime.DatetimeGregorian(2001, 4, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2001, 7, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2001, 10, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2002, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2002, 4, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2002, 7, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2002, 10, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2003, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2003, 4, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2003, 7, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2003, 10, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2004, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2004, 4, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2004, 7, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2004, 10, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2005, 1, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2005, 4, 1, 0, 0, 0, 0, has_year_zero=False),
     cftime.DatetimeGregorian(2005, 7, 1, 0, 0, 0, 0, has_year_zero=False)]
    """
    # Uses the Gregorian calendar - allows for adding/subtracting
    # datetime.timedelta in range calc
    start_cf = cftime.DatetimeGregorian(*start.timetuple()[:6])
    end_cf = cftime.DatetimeGregorian(*end.timetuple()[:6])

    res = cftime_offsets.cftime_range(
        offset.rollback(start_cf), offset.rollforward(end_cf), freq=offset
    )

    return [date_cls(*dt.timetuple()[:6]) for dt in res]


__all__ = ["to_offset", "generate_range"]
