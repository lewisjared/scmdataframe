import random

import numpy as np
import pytest

import scmdata

@pytest.fixture(params=[10, 10 ** 2, 10 ** 3, 10 ** 3.5, 10 ** 4, 10 ** 5, 10 ** 5.5])
def big_scmrun(request):
    length = int(request.param)
    t_steps = 750
    variables = ["Surface Air Temperature Change", "Surface Air Ocean Blended Temperature Change", "Effective Radiative Forcing", "Atmospheric Concentrations|CO2"]
    scenarios = ["ssp119", "ssp245", "ssp434", "ssp460", "ssp126", "esm-1pctCo2"]
    regions = ["World", "World|R5.2ASIA", "World|R5.2LAM", "World|R5.2MAF", "World|R5.2REF", "World|R5.2OECD", "World|Bunkers"]
    climate_models = ["MAGICC7", "MAGICC6", "MAGICC5", "Bill", "Bloggs"]

    return scmdata.ScmRun(
        np.random.random((length, t_steps)).T,
        index=range(1750, 1750 + t_steps),
        columns={
            "model": "unspecified",
            "variable": random.choices(variables, k=length),
            "unit": "unknown",
            "scenario": random.choices(scenarios, k=length),
            "region": random.choices(regions, k=length),
            "climate_model": random.choices(climate_models, k=length),
            "ensemble_member": range(length),
        }
    )


def test_recreate_from_timeseries(benchmark, big_scmrun):
    def recreate():
        return scmdata.ScmRun(big_scmrun.timeseries())


    benchmark.pedantic(recreate, iterations=2, rounds=5)


def test_filter(benchmark, big_scmrun):
    def variable_filter():
        return big_scmrun.filter(variable="Effective Radiative Forcing", year=range(1850, 1910 + 1))


    result = benchmark.pedantic(variable_filter, iterations=2, rounds=5)
    assert result.get_unique_meta("variable", no_duplicates=True) == "Effective Radiative Forcing"
    assert result["year"].iloc[0] == 1850
    assert result["year"].iloc[-1] == 1910


def test_get_unique_meta(benchmark, big_scmrun):
    def retrieve_unique_meta():
        return big_scmrun.get_unique_meta("variable")


    result = benchmark.pedantic(retrieve_unique_meta, iterations=2, rounds=5)
    assert len(result) > 0


def test_append(benchmark, big_scmrun):
    def append_runs():
        other = big_scmrun.copy()
        other["ensemble_member"] += max(other["ensemble_member"]) + 1

        return big_scmrun.append(other)


    benchmark.pedantic(append_runs, iterations=2, rounds=5)


def test_append_other_time_axis(benchmark, big_scmrun):
    other = big_scmrun.timeseries(time_axis="year")
    other.columns = other.columns.map(lambda x: x + max(other.columns) + 1)
    other = scmdata.ScmRun(other)
    other["ensemble_member"] += max(other["ensemble_member"]) + 1


    def append_runs_different_times():
        return scmdata.run_append([big_scmrun, other])


    benchmark.pedantic(append_runs_different_times, iterations=2, rounds=5)
