"""Controlled vocabularies and validation for the CRINK event file.

Every rule enforced here is documented in CODEBOOK.md. If you change one,
change the other in the same commit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

ACTORS: tuple[str, ...] = ("CHN", "RUS", "IRN", "PRK")

COLUMNS: tuple[str, ...] = (
    "event_id",
    "date",
    "date_precision",
    "date_basis",
    "participants",
    "sender",
    "receiver",
    "domain",
    "tie_type",
    "intensity",
    "verification",
    "description",
    "source_name",
    "source_url",
    "source_type",
    "source_url_2",
    "notes",
)

REQUIRED: tuple[str, ...] = (
    "event_id",
    "date",
    "date_precision",
    "date_basis",
    "participants",
    "domain",
    "tie_type",
    "intensity",
    "verification",
    "description",
    "source_name",
    "source_url",
    "source_type",
)

DATE_PRECISION = {"day": r"^\d{4}-\d{2}-\d{2}$", "month": r"^\d{4}-\d{2}$", "year": r"^\d{4}$"}
DATE_BASIS = {"occurred", "reported"}

DOMAINS = {
    "military",
    "diplomatic",
    "legal_institutional",
    "multilateral",
    "economic",
    "intelligence_cyber",
}

# tie_type -> domains it may appear in. Keeps coding consistent across coders.
TIE_TYPES: dict[str, set[str]] = {
    "joint_exercise": {"military"},
    "arms_transfer": {"military"},
    "technology_transfer": {"military", "economic"},
    "dual_use_supply": {"military", "economic"},
    "personnel_deployment": {"military"},
    "military_logistics": {"military"},
    "intelligence_sharing": {"intelligence_cyber"},
    "cyber_cooperation": {"intelligence_cyber"},
    "summit": {"diplomatic"},
    "high_level_visit": {"diplomatic"},
    "joint_statement": {"diplomatic"},
    "co_presence": {"diplomatic"},
    "strategic_agreement": {"legal_institutional"},
    "treaty_signature": {"legal_institutional"},
    "treaty_in_force": {"legal_institutional"},
    "org_accession": {"multilateral"},
    "unsc_veto": {"multilateral"},
    "unsc_vote": {"multilateral"},
    "unsc_abstention": {"multilateral"},
    "unsc_draft": {"multilateral"},
    "energy_trade": {"economic"},
    "sanctions_evasion": {"economic"},
}

VERIFICATION = {"A", "B", "C"}
SOURCE_TYPES = {
    "official_participant",
    "official_third_party",
    "intergovernmental",
    "media",
    "think_tank",
}

INTENSITY_MIN, INTENSITY_MAX = 1, 5
EVENT_ID = re.compile(r"^CRK-\d{4}$")


def split_codes(value: object) -> list[str]:
    """Split a semicolon list like 'CHN;RUS' into ['CHN', 'RUS']; blanks -> []."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(";") if part.strip()]


@dataclass(frozen=True)
class Problem:
    event_id: str
    field: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - formatting only
        return f"{self.event_id}: [{self.field}] {self.message}"


def validate(events: pd.DataFrame) -> list[Problem]:
    """Return every rule violation in the event table (empty list = valid)."""
    problems: list[Problem] = []

    missing_cols = [c for c in COLUMNS if c not in events.columns]
    if missing_cols:
        return [Problem("<file>", "columns", f"missing columns: {missing_cols}")]
    extra = [c for c in events.columns if c not in COLUMNS]
    if extra:
        problems.append(Problem("<file>", "columns", f"unexpected columns: {extra}"))

    dupes = events["event_id"][events["event_id"].duplicated()].tolist()
    for d in dupes:
        problems.append(Problem(str(d), "event_id", "duplicate event_id"))

    for _, row in events.iterrows():
        eid = str(row["event_id"])

        def bad(field: str, msg: str, eid: str = eid) -> None:
            problems.append(Problem(eid, field, msg))

        for col in REQUIRED:
            if pd.isna(row[col]) or str(row[col]).strip() == "":
                bad(col, "required field is empty")

        if not EVENT_ID.match(eid):
            bad("event_id", "must look like CRK-0001")

        prec = str(row["date_precision"])
        if prec not in DATE_PRECISION:
            bad("date_precision", f"must be one of {sorted(DATE_PRECISION)}")
        elif not re.match(DATE_PRECISION[prec], str(row["date"])):
            bad("date", f"'{row['date']}' does not match precision '{prec}'")
        else:
            try:
                pd.Period(str(row["date"]), freq={"day": "D", "month": "M", "year": "Y"}[prec])
            except (ValueError, TypeError):
                bad("date", f"'{row['date']}' is not a real date")

        if str(row["date_basis"]) not in DATE_BASIS:
            bad("date_basis", f"must be one of {sorted(DATE_BASIS)}")

        parts = split_codes(row["participants"])
        if len(parts) < 2:
            bad("participants", "need at least two CRINK states")
        if len(set(parts)) != len(parts):
            bad("participants", "duplicate code")
        unknown = [p for p in parts if p not in ACTORS]
        if unknown:
            bad("participants", f"unknown codes {unknown}; use {ACTORS}")

        senders, receivers = split_codes(row["sender"]), split_codes(row["receiver"])
        if bool(senders) != bool(receivers):
            bad("sender/receiver", "fill both or neither")
        for field, codes in (("sender", senders), ("receiver", receivers)):
            stray = [c for c in codes if c not in parts]
            if stray:
                bad(field, f"{stray} not listed in participants")
        if set(senders) & set(receivers):
            bad("sender/receiver", "a state cannot send to itself")

        domain, tie = str(row["domain"]), str(row["tie_type"])
        if domain not in DOMAINS:
            bad("domain", f"must be one of {sorted(DOMAINS)}")
        if tie not in TIE_TYPES:
            bad("tie_type", f"must be one of {sorted(TIE_TYPES)}")
        elif domain in DOMAINS and domain not in TIE_TYPES[tie]:
            bad("tie_type", f"'{tie}' is not allowed in domain '{domain}'")

        try:
            inten = int(row["intensity"])
            if not INTENSITY_MIN <= inten <= INTENSITY_MAX or float(row["intensity"]) != inten:
                raise ValueError
        except (ValueError, TypeError):
            bad("intensity", f"must be an integer {INTENSITY_MIN}-{INTENSITY_MAX}")

        if str(row["verification"]) not in VERIFICATION:
            bad("verification", f"must be one of {sorted(VERIFICATION)}")
        if str(row["source_type"]) not in SOURCE_TYPES:
            bad("source_type", f"must be one of {sorted(SOURCE_TYPES)}")

        for col in ("source_url", "source_url_2"):
            val = row[col]
            if pd.notna(val) and str(val).strip() and not str(val).startswith("https://"):
                bad(col, "must be an https:// URL")

    return problems
