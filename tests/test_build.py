from pathlib import Path

import pandas as pd
import pytest

from crink.build import (
    DYAD_LABELS,
    build,
    dyad_year_panel,
    expand_dyads,
    expand_flows,
    load_events,
    network_metrics,
)

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


@pytest.fixture
def toy() -> pd.DataFrame:
    rows = [
        # trilateral, unverified-ish: 3 dyads
        dict(event_id="CRK-9001", date="2020-01-01", date_precision="day", date_basis="occurred",
             participants="CHN;RUS;IRN", sender="", receiver="", domain="military",
             tie_type="joint_exercise", intensity="3", verification="B"),
        # directed, two senders: 2 flows, 3 dyads
        dict(event_id="CRK-9002", date="2021-05", date_precision="month", date_basis="occurred",
             participants="CHN;RUS;PRK", sender="CHN;RUS", receiver="PRK", domain="multilateral",
             tie_type="unsc_veto", intensity="3", verification="A"),
    ]
    df = pd.DataFrame(rows)
    df["intensity"] = df["intensity"].astype(int)
    df["year"] = df["date"].str[:4].astype(int)
    return df


def test_multilateral_expands_to_all_pairs(toy):
    d = expand_dyads(toy)
    assert len(d) == 6
    assert set(d[d.event_id == "CRK-9001"].dyad) == {"CHN-RUS", "CHN-IRN", "RUS-IRN"}


def test_dyad_labels_are_canonical(toy):
    assert set(expand_dyads(toy).dyad) <= set(DYAD_LABELS)


def test_verification_discount(toy):
    d = expand_dyads(toy)
    assert d[d.event_id == "CRK-9001"].weight.iloc[0] == pytest.approx(3 * 0.75)
    assert d[d.event_id == "CRK-9002"].weight.iloc[0] == pytest.approx(3.0)


def test_flows_only_from_coded_direction(toy):
    f = expand_flows(toy)
    assert len(f) == 2
    assert set(zip(f.sender, f.receiver, strict=True)) == {("CHN", "PRK"), ("RUS", "PRK")}


def test_panel_is_balanced_and_conserves_events(toy):
    years = range(2019, 2023)
    d = expand_dyads(toy)
    panel = dyad_year_panel(d, years)
    assert len(panel) == 6 * len(years)
    assert panel.n_events.sum() == len(d)
    assert not panel.isna().any().any()


def test_strength_shares_sum_to_one(toy):
    years = range(2020, 2022)
    m = network_metrics(dyad_year_panel(expand_dyads(toy), years), years)
    for _, grp in m.groupby("year"):
        assert grp.strength_share.sum() == pytest.approx(1.0, abs=0.01)


def test_full_build_runs(tmp_path):
    tables = build(RAW, tmp_path)
    events = load_events(RAW / "events.csv")
    assert len(tables["events"]) == len(events)
    assert (tmp_path / "dyad_year.csv").exists()
    assert (tmp_path / "graphs" / "crink_all_years.graphml").exists()


def test_min_verification_filters(tmp_path):
    strict = build(RAW, tmp_path, min_verification="A")
    assert set(strict["events"].verification) == {"A"}
