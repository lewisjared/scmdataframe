import warnings

import numpy as np
from xarray.core import ops
from xarray.core.common import ImplementsArrayReduce


def maybe_wrap_array(original, new_array):
    """
    Wrap a transformed array with __array_wrap__ if it can be done safely.

    This ensures that an array's metadata is maintained if it makes sense to do so (
    e.g. with masked arrays). It also lets us treat arbitrary functions that take and
    return ndarray objects like ufuncs, as long as they return an array with the same
    shape.
    """
    if isinstance(new_array, np.ndarray) and new_array.shape == original.shape:
        return original.__array_wrap__(new_array)
    else:
        return new_array


class GroupBy(ImplementsArrayReduce):
    def __init__(self, meta, groups, na_fill_value=-10000):
        m = meta.reset_index(drop=True)
        self.na_fill_value = float(na_fill_value)

        # Work around the bad handling of NaN values in groupbys
        if any([np.issubdtype(m[c].dtype, np.number) for c in m]):
            if (meta == na_fill_value).any(axis=None):
                raise ValueError(
                    "na_fill_value conflicts with data value. "
                    "Choose an na_fill_value not in meta"
                )

            m = m.fillna(na_fill_value)

        self._grouper = m.groupby(list(groups), group_keys=True)

    def _iter_grouped(self):
        def _try_fill_value(v):
            try:
                if float(v) == float(self.na_fill_value):
                    return np.nan

            except ValueError:  # not a number
                pass

            return v

        for indices in self._grouper.groups:
            indices = np.atleast_1d(indices)
            indices = [_try_fill_value(v) for v in indices]
            # TODO: check whether this method should be moved to ``RunGroupBy`` given
            # that it relies on ``self.run`` and ``self.group_keys`` (which aren't set
            # by ``__init__`` of ``GroupBy``)
            res = self.run.filter(**{k: v for k, v in zip(self.group_keys, indices)})
            assert len(res), "Empty group for {}".format(
                list(zip(self.group_keys, indices))
            )
            yield res


class RunGroupBy(GroupBy):
    """
    GroupBy object specialized to grouping ScmRun objects
    """

    def __init__(self, run, groups):
        self.run = run
        self.group_keys = groups
        super().__init__(run.meta, groups)

    def map(self, func, args=(), **kwargs):
        """
        Apply a function to each element in the group.

        ``func`` is called as ``func(ar, *args, **kwargs)`` for each array ``ar``
        in the group.

        # TODO: check whether the text below still applies given that
        # `pandas.GroupBy.apply` is no longer applied

        Apply uses heuristics (like `pandas.GroupBy.apply`) to figure out how
        to stack together the array. The rule is:

        1. If the dimension along which the group coordinate is defined is
           still in the first grouped array after applying `func`, then stack
           over this dimension.
        2. Otherwise, stack over the new dimension given by name of this
           grouping (the argument to the `groupby` function).

        Parameters
        ----------
        func : function
            Callable to apply to each element in the group.

        args : tuple, optional
            Positional arguments passed to ``func``.

        **kwargs
            Keyword arguments passed to ``func``.

        Returns
        -------
        applied : :obj:`ScmDataFrame` or None
            The result of splitting, applying and combining this array.
        """
        grouped = self._iter_grouped()
        applied = [maybe_wrap_array(arr, func(arr, *args, **kwargs)) for arr in grouped]
        return self._combine(applied)

    def _combine(self, applied):
        """Recombine the applied objects like the original."""
        # TODO: is this here to avoid a circular import?
        from scmdata.run import df_append

        # Remove all None values
        applied = [df for df in applied if df is not None]

        if len(applied) == 0:
            return None
        else:
            return df_append(applied)

    def reduce(
        self, func, dim=None, axis=None, **kwargs
    ):
        """
        Reduce the items in this group by applying ``func`` along some
        dimension(s).

        Parameters
        ----------
        func : function
            Function which can be called in the form
            ``func(x, axis=axis, **kwargs)`` to return the result of collapsing
            an :obj:`np.ndarray` over an integer valued axis.

        dim : `...`, str or sequence of str, optional
            Not used in this implementation

        axis : int or sequence of int, optional
            Axis(axes) over which to apply ``func``. Only one of the 'dimension'
            and 'axis' arguments can be supplied. If neither are supplied, then
            ``func`` is calculated over all dimension for each group item.

        **kwargs : dict
            Additional keyword arguments passed on to ``func``.

        Returns
        -------
        reduced : :obj:`ScmRun` or None
            :obj:`ScmRun` with summarized data and the indicated dimension(s)
            removed.

        Raises
        ------
        AssertionError
            ``dim`` is not ``None`` or ``"time"``.
        """
        if dim is not None:
            assert dim is "time", "Only reduction along the time dimension is supported"

        def reduce_array(ar):
            return ar.reduce(func, dim, axis, **kwargs)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            return self.map(reduce_array)


ops.inject_reduce_methods(RunGroupBy)
