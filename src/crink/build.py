"""Turn the hand-coded event file into analysis-ready network tables.

Pipeline:  events.csv  ->  dyad_events  ->  dyad_year panel  ->  yearly graphs + metrics

Design choices (all documented in CODEBOOK.md, section 5):
* A multilateral event among k CRINK states becomes k*(k-1)/2 undirected dyad rows.
* Directed rows are produced only where sender/receiver are coded.
* Edge weight = intensity x verification weight, so contested claims count less.
* The dyad-year panel is balanced: every dyad appears in every year, zeros filled.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import networkx as nx
import pandas as pd

from .schema import ACTORS, split_codes, validate

# Default discount for less-verified events. Override for robustness checks.
VERIFICATION_WEIGHTS: dict[str, float] = {"A": 1.0, "B": 0.75, "C": 0.5}

DYADS: list[tuple[str, str]] = list(itertools.combinations(ACTORS, 2))
DYAD_LABELS: list[str] = [f"{a}-{b}" for a, b in DYADS]


def dyad_label(x: str, y: str) -> str:
    a, b = sorted((x, y), key=ACTORS.index)
    return f"{a}-{b}"


def load_events(path: str | Path, *, check: bool = True) -> pd.DataFrame:
    """Read events.csv as text, validate it, and add typed helper columns."""
    events = pd.read_csv(path, dtype=str, keep_default_na=False)
    if check:
        problems = validate(events)
        if problems:
            listing = "\n".join(f"  - {p}" for p in problems)
            raise ValueError(f"{len(problems)} problem(s) in {path}:\n{listing}")
    events = events.copy()
    events["intensity"] = events["intensity"].astype(int)
    events["year"] = events["date"].str[:4].astype(int)
    return events


def _weight(row: pd.Series, weights: dict[str, float]) -> float:
    return row["intensity"] * weights[row["verification"]]


def expand_dyads(events: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """One row per (event, unordered CRINK pair)."""
    weights = weights or VERIFICATION_WEIGHTS
    rows = []
    for _, ev in events.iterrows():
        parts = split_codes(ev["participants"])
        for x, y in itertools.combinations(parts, 2):
            rows.append(
                {
                    "event_id": ev["event_id"],
                    "year": ev["year"],
                    "dyad": dyad_label(x, y),
                    "domain": ev["domain"],
                    "tie_type": ev["tie_type"],
                    "intensity": ev["intensity"],
                    "verification": ev["verification"],
                    "weight": _weight(ev, weights),
                    "n_participants": len(parts),
                }
            )
    return pd.DataFrame(rows)


def expand_flows(events: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """One row per (event, sender, receiver) for directed ties."""
    weights = weights or VERIFICATION_WEIGHTS
    rows = []
    for _, ev in events.iterrows():
        for s, r in itertools.product(split_codes(ev["sender"]), split_codes(ev["receiver"])):
            rows.append(
                {
                    "event_id": ev["event_id"],
                    "year": ev["year"],
                    "sender": s,
                    "receiver": r,
                    "domain": ev["domain"],
                    "tie_type": ev["tie_type"],
                    "intensity": ev["intensity"],
                    "verification": ev["verification"],
                    "weight": _weight(ev, weights),
                }
            )
    cols = ["event_id", "year", "sender", "receiver", "domain", "tie_type",
            "intensity", "verification", "weight"]
    return pd.DataFrame(rows, columns=cols)


def dyad_year_panel(dyad_events: pd.DataFrame, years: range) -> pd.DataFrame:
    """Balanced dyad x year panel with counts, intensity and per-domain counts."""
    grid = pd.MultiIndex.from_product([DYAD_LABELS, list(years)], names=["dyad", "year"])
    g = dyad_events.groupby(["dyad", "year"])
    panel = pd.DataFrame(
        {
            "n_events": g.size(),
            "sum_intensity": g["intensity"].sum(),
            "max_intensity": g["intensity"].max(),
            "weighted_intensity": g["weight"].sum(),
            "n_verified_A": g["verification"].apply(lambda s: int((s == "A").sum())),
        }
    )
    by_domain = (
        dyad_events.pivot_table(index=["dyad", "year"], columns="domain",
                                values="event_id", aggfunc="count")
        .add_prefix("n_")
    )
    panel = panel.join(by_domain).reindex(grid).fillna(0)
    panel = panel.astype({c: int for c in panel.columns if c != "weighted_intensity"})
    panel["weighted_intensity"] = panel["weighted_intensity"].round(3)
    panel = panel.reset_index()
    panel[["actor_a", "actor_b"]] = panel["dyad"].str.split("-", expand=True)
    first = ["dyad", "actor_a", "actor_b", "year"]
    return panel[first + [c for c in panel.columns if c not in first]]


def graph_for(panel: pd.DataFrame, year: int | None = None) -> nx.Graph:
    """Weighted undirected graph for one year (or the whole period if year is None)."""
    sub = panel if year is None else panel[panel["year"] == year]
    agg = sub.groupby(["actor_a", "actor_b"])[["n_events", "weighted_intensity"]].sum()
    graph = nx.Graph(year=str(year) if year is not None else "all")
    graph.add_nodes_from(ACTORS)
    for (a, b), r in agg.iterrows():
        if r["n_events"] > 0:
            graph.add_edge(a, b, weight=float(r["weighted_intensity"]),
                           n_events=int(r["n_events"]))
    return graph


def network_metrics(panel: pd.DataFrame, years: range) -> pd.DataFrame:
    """Per state-year: weighted degree (strength), its share, and network density."""
    rows = []
    for year in years:
        g = graph_for(panel, year)
        total = sum(d["weight"] for _, _, d in g.edges(data=True))
        density = nx.density(g)
        for node in ACTORS:
            strength = g.degree(node, weight="weight")
            rows.append(
                {
                    "year": year,
                    "actor": node,
                    "degree": g.degree(node),
                    "strength": round(strength, 3),
                    # each edge counts toward two nodes, so shares sum to 1 via 2*total
                    "strength_share": round(strength / (2 * total), 3) if total else 0.0,
                    "network_density": round(density, 3),
                    "network_total_weight": round(total, 3),
                }
            )
    return pd.DataFrame(rows)


def build(raw_dir: str | Path, out_dir: str | Path,
          weights: dict[str, float] | None = None,
          min_verification: str = "C") -> dict[str, pd.DataFrame]:
    """Run the whole pipeline and write every output. Returns the tables.

    min_verification="A" keeps only participant-confirmed events, "B" drops C, "C" keeps all.
    """
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    (out_dir / "graphs").mkdir(parents=True, exist_ok=True)

    events = load_events(raw_dir / "events.csv")
    years = range(int(events["year"].min()), int(events["year"].max()) + 1)
    events = events[events["verification"] <= min_verification].reset_index(drop=True)

    dyads = expand_dyads(events, weights)
    flows = expand_flows(events, weights)
    panel = dyad_year_panel(dyads, years)
    metrics = network_metrics(panel, years)

    dyads.to_csv(out_dir / "dyad_events.csv", index=False)
    flows.to_csv(out_dir / "directed_flows.csv", index=False)
    panel.to_csv(out_dir / "dyad_year.csv", index=False)
    metrics.to_csv(out_dir / "network_metrics_year.csv", index=False)

    for year in list(years) + [None]:
        g = graph_for(panel, year)
        name = f"crink_{year}" if year is not None else "crink_all_years"
        nx.write_graphml(g, out_dir / "graphs" / f"{name}.graphml")
        with open(out_dir / "graphs" / f"{name}.json", "w", encoding="utf-8") as fh:
            json.dump(nx.node_link_data(g, edges="links"), fh, indent=2)

    return {"events": events, "dyad_events": dyads, "directed_flows": flows,
            "dyad_year": panel, "network_metrics_year": metrics}
