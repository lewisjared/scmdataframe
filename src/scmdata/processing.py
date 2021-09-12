"""
Miscellaneous functions for processing :class:`scmdata.ScmRun`

These functions are intended to be able to be used directly with
:meth:`scmdata.ScmRun.process_over`.
"""
import numpy as np
import pandas as pd
import tqdm.autonotebook as tqdman

from .run import ScmRun


def _get_ts_gt_threshold(scmrun, threshold):
    timeseries = scmrun.timeseries()

    return timeseries > threshold


def calculate_crossing_times(scmrun, threshold, return_year=True):
    """
    Calculate the time at which each timeseries crosses a given threshold

    Parameters
    ----------
    scmrun : :class:`scmdata.ScmRun`
        Data to calculate the crossing time of

    threshold : float
        Value to use as the threshold for crossing

    return_year : bool
        If ``True``, return the year instead of the datetime

    Returns
    -------
    :class:`pd.Series`
        Crossing time for ``scmrun``, using the meta of ``scmrun`` as the
        output's index. If the threshold is not crossed, ``pd.NA`` is returned.

    Notes
    -----
    This function only returns times that are in the columns of ``scmrun``. If
    you want a finer resolution then you should interpolate your data first.
    For example, if you have data on a ten-year timestep but want crossing
    times on an annual resolution, interpolate (or resample) to annual data
    before calling ``calculate_crossing_times``.
    """
    timeseries_gt_threshold = _get_ts_gt_threshold(scmrun, threshold)
    out = timeseries_gt_threshold.idxmax(axis=1)

    if return_year:
        out = out.apply(lambda x: x.year).astype(int)

    # if don't cross, set to nan
    out[~timeseries_gt_threshold.any(axis=1)] = np.nan

    return out


def _assert_only_one_value(scmrun, col):
    if len(scmrun.get_unique_meta(col)) > 1:
        raise ValueError(
            "More than one value for {}. "
            "This is unlikely to be what you want.".format(col)
        )


def _get_exceedance_fraction(ts, group_cols):
    grouper = ts.groupby(group_cols)
    number_exceeding = grouper.sum()
    number_members = grouper.count()
    out = number_exceeding / number_members

    return out


_DEFAULT_EXCEEDANCE_PROB_OUTPUT_BASE = "{} exceedance probability"


def _get_exceedance_prob_output_name(output_name, threshold):
    if output_name is None:
        return _DEFAULT_EXCEEDANCE_PROB_OUTPUT_BASE.format(threshold)

    return output_name


def _set_index_level_to(inp, col, val):
    inp.index = inp.index.set_levels([val], level=col)

    return inp


def calculate_exceedance_probabilities(
    scmrun, threshold, process_over_cols, output_name=None
):
    """
    Calculate exceedance probability over all time

    Parameters
    ----------
    scmrun : :class:`scmdata.ScmRun`
        Ensemble of which to calculate the exceedance probability

    threshold : float
        Value to use as the threshold for exceedance

    process_over_cols : list[str]
        Columns to not use when grouping the timeseries (typically "run_id" or
        "ensemble_member" or similar)

    output_name : str
        If supplied, the name of the output series. If not supplied,
        "{threshold} exceedance probability" will be used.

    Returns
    -------
    :class:`pd.Series`
        Exceedance probability over all time over all members of each group in
        ``scmrun``

    Raises
    ------
    ValueError
        ``scmrun`` has more than one variable or more than one unit (convert to
        a single unit before calling this function if needed)

    Notes
    -----
    See the notes of
    :func:`scmdata.processing.calculate_exceedance_probabilities_over_time`
    for an explanation of how the two calculations differ. For most purposes,
    this is the correct function to use.
    """
    _assert_only_one_value(scmrun, "variable")
    _assert_only_one_value(scmrun, "unit")
    timeseries_gt_threshold = _get_ts_gt_threshold(scmrun, threshold)
    group_cols = list(scmrun.get_meta_columns_except(process_over_cols))

    out = _get_exceedance_fraction(timeseries_gt_threshold.any(axis=1), group_cols,)

    if not isinstance(out, pd.Series):  # pragma: no cover # emergency valve
        raise AssertionError("How did we end up without a series?")

    output_name = _get_exceedance_prob_output_name(output_name, threshold)
    out.name = output_name
    out = _set_index_level_to(out, "unit", "dimensionless")

    return out


def calculate_exceedance_probabilities_over_time(
    scmrun, threshold, process_over_cols, output_name=None
):
    """
    Calculate exceedance probability at each point in time

    Parameters
    ----------
    scmrun : :class:`scmdata.ScmRun`
        Ensemble of which to calculate the exceedance probability over time

    threshold : float
        Value to use as the threshold for exceedance

    process_over_cols : list[str]
        Columns to not use when grouping the timeseries (typically "run_id" or
        "ensemble_member" or similar)

    output_name : str
        If supplied, the value to put in the "variable" columns of the output
        :class:`pd.DataFrame`. If not supplied, "{threshold} exceedance
        probability" will be used.

    Returns
    -------
    :class:`pd.DataFrame`
        Timeseries of exceedance probability over time

    Raises
    ------
    ValueError
        ``scmrun`` has more than one variable or more than one unit (convert to
        a single unit before calling this function if needed)

    Notes
    -----
    This differs from
    :func:`scmdata.processing.calculate_exceedance_probabilities` because it
    calculates the exceedance probability at each point in time. That is
    different from calculating the exceedance probability by first determining
    the number of ensemble members which cross the threshold **at any point in
    time** and then dividing by the number of ensemble members. In general,
    this function will produce a maximum exceedance probability which is equal
    to or less than the output of
    :func:`scmdata.processing.calculate_exceedance_probabilities`. In our
    opinion, :func:`scmdata.processing.calculate_exceedance_probabilities` is
    the correct function to use if you want to know the exceedance probability
    of a scenario. This function gives a sense of how the exceedance
    probability evolves over time but, as we said, will generally slightly
    underestimate the exceedance probability over all time.
    """
    _assert_only_one_value(scmrun, "variable")
    _assert_only_one_value(scmrun, "unit")
    timeseries_gt_threshold = _get_ts_gt_threshold(scmrun, threshold)
    group_cols = list(scmrun.get_meta_columns_except(process_over_cols))

    out = _get_exceedance_fraction(timeseries_gt_threshold, group_cols,)

    if not isinstance(out, pd.DataFrame):  # pragma: no cover # emergency valve
        raise AssertionError("How did we end up without a dataframe?")

    output_name = _get_exceedance_prob_output_name(output_name, threshold)
    out = _set_index_level_to(out, "variable", output_name)
    out = _set_index_level_to(out, "unit", "dimensionless")

    return out


def _set_peak_output_name(out, output_name, default_lead):
    if output_name is not None:
        out = _set_index_level_to(out, "variable", output_name)
    else:
        idx = out.index.names
        out = out.reset_index()
        out["variable"] = out["variable"].apply(
            lambda x: "{} {}".format(default_lead, x)
        )
        out = out.set_index(idx)[0]

    return out


def calculate_peak(scmrun, output_name=None):
    """
    Calculate peak i.e. maximum of each timeseries

    Parameters
    ----------
    scmrun : :class:`scmdata.ScmRun`
        Ensemble of which to calculate the exceedance probability over time

    output_name : str
        If supplied, the value to put in the "variable" columns of the output
        series. If not supplied, "Peak {variable}" will be used.

    Returns
    -------
    :class:`pd.Series`
        Peak of each timeseries
    """
    out = scmrun.timeseries().max(axis=1)
    out = _set_peak_output_name(out, output_name, "Peak")

    return out


def calculate_peak_time(scmrun, output_name=None, return_year=True):
    """
    Calculate peak time i.e. the time at which each timeseries reaches its maximum

    Parameters
    ----------
    scmrun : :class:`scmdata.ScmRun`
        Ensemble of which to calculate the exceedance probability over time

    output_name : str
        If supplied, the value to put in the "variable" columns of the output
        series. If not supplied, "Peak {variable}" will be used.

    return_year : bool
        If ``True``, return the year instead of the datetime

    Returns
    -------
    :class:`pd.Series`
        Peak of each timeseries
    """
    out = scmrun.timeseries().idxmax(axis=1)
    if return_year:
        out = out.apply(lambda x: x.year)

    out = _set_peak_output_name(
        out, output_name, "Year of peak" if return_year else "Time of peak"
    )

    return out


def categorisation_sr15(scmrun, index):
    """
    Categorise using the algorithm employed in SR1.5

    For more information, see ``_ [TODO link to notebooks].

    Parameters
    ----------
    scmrun : :class: `scmdata.ScmRun`
        Data to use for the classification

    index : list[str]
        Columns in ``scmrun.meta`` to use as the index of the output

    Returns
    -------
    :class: `pd.Series`
        Categorisation of the timeseries

    Raises
    ------
    ValueError
        More than one variable or one unit is in ``scmrun``

    DimensionalityError
        The units cannot be converted to kelvin
    """
    _assert_only_one_value(scmrun, "variable")
    scmrun = scmrun.convert_unit("K")
    scmrun["unit"] = ""

    categories = pd.Series(
        name="category",
        index=pd.MultiIndex.from_frame(scmrun.meta[index].drop_duplicates()),
        dtype="object",
    )

    def _get_comp_series(res):
        reset_cols = list(set(res.index.names) - set(index))
        out = res.reset_index(reset_cols, drop=True).reorder_levels(index)

        return out

    peak_median = _get_comp_series(calculate_peak(scmrun.filter(quantile=0.5)))
    peak_p33 = _get_comp_series(calculate_peak(scmrun.filter(quantile=0.33)))
    peak_p66 = _get_comp_series(calculate_peak(scmrun.filter(quantile=0.66)))
    end_of_century_median = _get_comp_series(
        calculate_peak(scmrun.filter(quantile=0.5, year=2100))
    )
    categories[peak_median > 2.0] = "Above 2C"
    categories[peak_median <= 1.5] = "Below 1.5C"

    overshoot_15 = (peak_median > 1.5) & (end_of_century_median <= 1.5)
    categories[
        overshoot_15 & (peak_p33 <= 1.5)  # p exceed <= 0.67
    ] = "1.5C low overshoot"
    categories[
        overshoot_15 & (peak_p33 > 1.5)  # p exceed > 0.67
    ] = "1.5C high overshoot"

    still_uncategorised = categories.isnull()
    peak_p66_lte_2 = peak_p66 <= 2.0  # p exceed < 0.34
    categories[
        still_uncategorised & (peak_median <= 2.0) & ~peak_p66_lte_2
    ] = "Higher 2C"
    categories[still_uncategorised & peak_p66_lte_2] = "Lower 2C"

    if categories.isnull().any():  # pragma: no cover # emergency valve
        raise AssertionError("Unclassified results?")

    return categories


def _calculate_quantile_groupby(base, index, quantile):
    return base.groupby(index).quantile(quantile)


def calculate_summary_stats(
    scmrun,
    index,
    exceedance_probabilities_thresholds=(1.5, 2.0, 2.5),
    exceedance_probabilities_variable="Surface Air Temperature Change",
    exceedance_probabilities_naming_base=None,
    peak_quantiles=(0.05, 0.17, 0.5, 0.83, 0.95),
    peak_variable="Surface Air Temperature Change",
    peak_naming_base=None,
    peak_time_naming_base=None,
    peak_return_year=True,
    categorisation_variable="Surface Air Temperature Change",
    categorisation_quantile_cols=("ensemble_member",),
    progress=False,
):
    """
    Calculate common summary statistics

    Parameters
    ----------
    scmrun : :class:`scmdata.ScmRun`
        Data of which to calculate the stats

    index : list[str]
        Columns to use in the index of the output (unit is added if not
        included)

    exceedance_probabilities_threshold : list[float]
        Thresholds to use for exceedance probabilities

    exceedance_probabilities_variable : str
        Variable to use for exceedance probability calculations

    exceedance_probabilities_naming_base : str
        String to use as the base for naming the exceedance probabilities. Each
        exceedance probability output column will have a name given by
        ``exceedance_probabilities_naming_base.format(threshold)`` where
        threshold is the exceedance probability threshold to use. If not
        supplied, the default output of
        :func:`scmdata.processing.calculate_exceedance_probabilities` will be
        used.

    peak_quantiles : list[float]
        Quantiles to report in peak calculations

    peak_variable : str
        Variable of which to calculate the peak

    peak_naming_base : str
        Base to use for naming the peak outputs. This is combined with the
        quantile. If not supplied, ``"{} peak"`` is used so the outputs will be
        named e.g. "0.05 peak", "0.5 peak", "0.95 peak".

    peak_time_naming_base : str
        Base to use for naming the peak time outputs. This is combined with the
        quantile. If not supplied, ``"{} peak year"`` is used (unless
        ``peak_return_year`` is ``False`` in which case ``"{} peak time"`` is
        used) so the outputs will be named e.g. "0.05 peak year", "0.5 peak
        year", "0.95 peak year".

    peak_return_year : bool
        If ``True``, return the year of the peak of ``peak_variable``,
        otherwise return full dates

    progress : bool
        Should a progress bar be shown whilst the calculations are done?

    Returns
    -------
    :class:`pd.DataFrame`
        Summary statistics, with each column being a statistic and the index
        being given by ``index``
    """
    if "unit" not in index:
        _index = index + ["unit"]
    else:
        _index = index

    process_over_cols = scmrun.get_meta_columns_except(_index)

    if exceedance_probabilities_naming_base is None:
        exceedance_probabilities_naming_base = _DEFAULT_EXCEEDANCE_PROB_OUTPUT_BASE

    scmrun_exceedance_prob = scmrun.filter(
        variable=exceedance_probabilities_variable, log_if_empty=False,
    )
    if scmrun_exceedance_prob.empty:
        msg = (
            "exceedance_probabilities_variable `{}` is not available. "
            "Available variables:{}".format(
                exceedance_probabilities_variable, scmrun.get_unique_meta("variable")
            )
        )
        raise ValueError(msg)

    exceedance_prob_calls = [
        (
            calculate_exceedance_probabilities,
            [scmrun_exceedance_prob, t, process_over_cols],
            {"output_name": exceedance_probabilities_naming_base.format(t)},
            exceedance_probabilities_naming_base.format(t),
        )
        for t in exceedance_probabilities_thresholds
    ]

    if peak_naming_base is None:
        peak_naming_base = "{} peak"

    if peak_time_naming_base is None:
        if peak_return_year:
            peak_time_naming_base = "{} peak year"
        else:
            peak_time_naming_base = "{} peak time"

    scmrun_peak = scmrun.filter(variable=peak_variable, log_if_empty=False,)
    if scmrun_peak.empty:
        msg = "peak_variable `{}` is not available. " "Available variables:{}".format(
            peak_variable, scmrun.get_unique_meta("variable")
        )
        raise ValueError(msg)

    # pre-calculate to avoid calculating multiple times
    peaks = calculate_peak(scmrun_peak)
    peak_calls = [
        (
            _calculate_quantile_groupby,
            [peaks, _index, q],
            {},
            peak_naming_base.format(q),
        )
        for q in peak_quantiles
    ]

    # pre-calculate to avoid calculating multiple times
    peak_times = calculate_peak_time(scmrun_peak, return_year=peak_return_year)
    peak_time_calls = [
        (
            _calculate_quantile_groupby,
            [peak_times, _index, q],
            {},
            peak_time_naming_base.format(q),
        )
        for q in peak_quantiles
    ]

    scmrun_categorisation = scmrun.filter(variable=categorisation_variable)
    if scmrun_categorisation.empty:
        # TODO: remove duplication
        msg = "categorisation_variable `{}` is not available. " "Available variables:{}".format(
            categorisation_variable, scmrun.get_unique_meta("variable")
        )
        raise ValueError(msg)

    if isinstance(categorisation_quantile_cols, str):
        categorisation_quantile_cols = [categorisation_quantile_cols]
    if not all([v in scmrun_categorisation.meta for v in categorisation_quantile_cols]):
        msg = "categorisation_quantile_cols `{}` not in `scmrun`. " "Available columns:{}".format(
            categorisation_quantile_cols, scmrun.meta.columns.tolist()
        )
        raise ValueError(msg)

    scmrun_categorisation = ScmRun(
        scmrun_categorisation
        .quantiles_over(
            cols=categorisation_quantile_cols,
            quantiles=[0.33, 0.5, 0.66],
        )
    )
    categorisation_calls = [
        (
            categorisation_sr15,
            [scmrun_categorisation, _index],
            {},
            "SR1.5 category",
        )
    ]
    func_calls_args_kwargs = exceedance_prob_calls + peak_calls + peak_time_calls + categorisation_calls

    if progress:
        iterator = tqdman.tqdm(func_calls_args_kwargs)
    else:
        iterator = func_calls_args_kwargs

    def get_result(func, args, kwargs, name):
        res = func(*args, **kwargs)
        res.name = name

        return res

    series = [
        get_result(func, args, kwargs, name).reorder_levels(_index)
        for func, args, kwargs, name in iterator
    ]
    if not peak_return_year:
        series = [s.astype("object") for s in series]

    out = pd.DataFrame(series).T

    out.columns.name = "statistic"
    out = out.stack("statistic")
    out.name = "value"

    return out
