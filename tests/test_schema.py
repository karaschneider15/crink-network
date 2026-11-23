from pathlib import Path

import pandas as pd
import pytest

from crink.schema import TIE_TYPES, validate

EVENTS = Path(__file__).resolve().parents[1] / "data" / "raw" / "events.csv"


@pytest.fixture
def events() -> pd.DataFrame:
    return pd.read_csv(EVENTS, dtype=str, keep_default_na=False)


def test_shipped_data_is_valid(events):
    problems = validate(events)
    assert problems == [], "\n".join(map(str, problems))


def test_every_event_has_a_source(events):
    assert (events["source_url"].str.startswith("https://")).all()


def _one(events, **changes):
    row = events.iloc[[0]].copy()
    for k, v in changes.items():
        row[k] = v
    return validate(row)


@pytest.mark.parametrize(
    "changes, field",
    [
        ({"participants": "CHN"}, "participants"),
        ({"participants": "CHN;USA"}, "participants"),
        ({"intensity": "7"}, "intensity"),
        ({"verification": "D"}, "verification"),
        ({"date": "2024-13-01"}, "date"),
        ({"date_precision": "month"}, "date"),
        ({"tie_type": "summit"}, "tie_type"),  # summit not allowed in military domain
        ({"sender": "PRK", "receiver": "RUS"}, "sender"),  # not among participants
        ({"sender": "CHN", "receiver": ""}, "sender/receiver"),
        ({"source_url": "http://insecure.example"}, "source_url"),
        ({"event_id": "X-1"}, "event_id"),
    ],
)
def test_validator_catches(events, changes, field):
    fields = {p.field for p in _one(events, **changes)}
    assert field in fields


def test_duplicate_ids_caught(events):
    doubled = pd.concat([events.iloc[[0]], events.iloc[[0]]])
    assert any(p.message == "duplicate event_id" for p in validate(doubled))


def test_every_tie_type_has_a_domain():
    assert all(TIE_TYPES.values())
