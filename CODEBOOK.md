# CRINK Network Dataset — Codebook

Version 0.1.0 · Coverage 2019-01-01 to 2026-11-23

This codebook is the specification. `src/crink/schema.py` enforces it, and CI fails any commit that breaks it. If you change a rule, change both files in the same commit.

---

## 1. Unit of observation

The unit is the **event**: a discrete, dated, publicly reported interaction that creates, reveals or formalises cooperation between **two or more** of the four states:

| Code | State | COW code |
|---|---|---|
| `CHN` | People's Republic of China | 710 |
| `RUS` | Russian Federation | 365 |
| `IRN` | Islamic Republic of Iran | 630 |
| `PRK` | Democratic People's Republic of Korea | 731 |

ISO-3166 alpha-3 codes are used throughout. COW codes are in `data/raw/actors.csv` so the data can be merged with Correlates of War, ATOP and other datasets.

**Inclusion rule.** Code an event when the interaction itself involves at least two CRINK states as actors or as the explicit beneficiary. Exclude:

- events where they only share a position but do not interact (for example, separate statements condemning the same strike),
- third-party actions that do not reveal a CRINK tie, unless the third party's evidence is the only record of that tie (for example, a Ukrainian strike on a ship said to carry Russia–Iran cargo is coded as evidence of the logistics tie, *not* as a Ukraine event).

**Seed-dataset caveat.** v0.1 contains high-salience events only. The absence of an event in a dyad-year means *nothing was coded*. It does **not** mean there was no tie. Section 7 sets out the plan for systematic coverage.

---

## 2. Variables (`data/raw/events.csv`)

| Variable | Type | Required | Definition |
|---|---|---|---|
| `event_id` | `CRK-####` | ✓ | Stable identifier. Never reuse or renumber. |
| `date` | ISO date | ✓ | `YYYY-MM-DD`, `YYYY-MM` or `YYYY`, matching `date_precision`. |
| `date_precision` | `day` / `month` / `year` | ✓ | The finest precision the sources support. If sources disagree on the day, code the month. |
| `date_basis` | `occurred` / `reported` | ✓ | `occurred` = when the interaction happened. `reported` = when it became public (used when the occurrence date is unknown, as with intelligence disclosures). |
| `participants` | `;`-list | ✓ | All CRINK states involved, two to four codes. |
| `sender` | `;`-list | — | For directed ties only: the providing state(s). |
| `receiver` | `;`-list | — | For directed ties only: the receiving or benefiting state(s). Fill both `sender` and `receiver` or neither. Leave both blank when direction is disputed. |
| `domain` | category | ✓ | See §3. |
| `tie_type` | category | ✓ | See §3. Each type is allowed only in certain domains. |
| `intensity` | int 1–5 | ✓ | See §4. |
| `verification` | `A` / `B` / `C` | ✓ | See §5. |
| `description` | text | ✓ | One neutral sentence in the coder's own words. No quotes over 15 words. |
| `source_name` | text | ✓ | Outlet or issuing body. |
| `source_url` | https URL | ✓ | The best available source. Prefer primary sources (§6). |
| `source_type` | category | ✓ | `official_participant`, `official_third_party`, `intergovernmental`, `media`, `think_tank`. |
| `source_url_2` | https URL | — | A corroborating source. |
| `notes` | text | — | Disagreements between sources, denials, coding judgement calls. |

---

## 3. Domains and tie types

| Domain | Allowed `tie_type` values |
|---|---|
| `military` | `joint_exercise`, `arms_transfer`, `technology_transfer`, `dual_use_supply`, `personnel_deployment`, `military_logistics` |
| `intelligence_cyber` | `intelligence_sharing`, `cyber_cooperation` |
| `diplomatic` | `summit` (leader–leader), `high_level_visit` (minister, premier, or senior party/security official), `joint_statement`, `co_presence` (leaders at the same event without a bilateral) |
| `legal_institutional` | `strategic_agreement`, `treaty_signature`, `treaty_in_force` |
| `multilateral` | `org_accession`, `unsc_veto`, `unsc_vote`, `unsc_abstention`, `unsc_draft` |
| `economic` | `energy_trade`, `sanctions_evasion`, `technology_transfer`, `dual_use_supply` |

`technology_transfer` and `dual_use_supply` can be coded as military or economic. Use `military` when the source ties the goods to weapons production.

---

## 4. Intensity (ordinal, 1–5)

Intensity records **commitment and material consequence**, not newsworthiness.

| Score | Label | Typical tie types |
|---|---|---|
| 1 | Passive alignment | UNSC abstention that benefits a partner |
| 2 | Diplomatic engagement | summits, high-level visits, co-presence, UNSC votes, joining the same organisation |
| 3 | Institutionalised or costly political cooperation | strategic agreements, partnership treaties without a defence clause, joint exercises, vetoes, sustained energy trade, sanctions evasion |
| 4 | Material military support or a defence commitment signed | arms, technology and dual-use transfers, non-combat personnel, intelligence sharing, military logistics, signing a treaty with a mutual assistance clause |
| 5 | Combat or a binding defence commitment in force | troops in combat, a mutual-defence treaty in force |

Rules:

1. Code the **highest** level the event clearly meets.
2. A treaty's signature and entry into force are **separate events**. A treaty without a defence clause scores 3 at both stages.
3. Vetoes score 3 because they impose costs and change outcomes. Votes score 2 and abstentions 1.

---

## 5. Verification grade

Some of these ties are deliberately hidden, so the evidence behind them varies widely. The grade records how strong the evidence is. It follows NATO/IC confidence language without claiming to be an intelligence judgement.

| Grade | Meaning | Default weight |
|---|---|---|
| **A** | Confirmed by at least one participant government, or a matter of public record (UN votes, treaties) | 1.00 |
| **B** | Attributed with specifics by a named third-party government or IO (US, MSMT, UN panel), or shown by multiple independent data sources (such as tanker tracking). The participants deny it or are silent. | 0.75 |
| **C** | A single-source or anonymously sourced claim that the reporting outlet could not independently confirm | 0.50 |

Regrade an event when the evidence changes. For example, the North Korean deployment to Kursk was B in late 2024 and became A once both governments confirmed it in April 2025. Record the change in `notes`.

**Edge weight** in all outputs = `intensity × verification weight`. Run `crink build --min-verification A` (or `B`) for robustness checks that drop weaker evidence entirely.

---

## 6. Sourcing standard

Prefer sources in this order:

1. Primary participant documents: MFA readouts, treaty texts, KCNA, Kremlin, Xinhua.
2. IO records: UN press releases and documents.
3. Named third-party government documents: US Treasury/State, MSMT reports.
4. Wire services and major outlets.
5. Think tanks.

Every event needs at least one `https` URL. Where sources disagree on dates, figures or direction, record the disagreement in `notes` rather than resolving it silently.

---

## 7. Derived outputs (`data/processed/`, regenerated by `crink build`)

| File | Unit | Notes |
|---|---|---|
| `dyad_events.csv` | event × unordered pair | An event among *k* states produces *k(k−1)/2* rows. `n_participants` records *k*, so multilateral events can be down-weighted or dropped. |
| `directed_flows.csv` | event × sender × receiver | Only for events with coded direction. |
| `dyad_year.csv` | dyad × year (balanced, zero-filled) | `n_events`, `sum_intensity`, `max_intensity`, `weighted_intensity`, `n_verified_A`, `n_<domain>` |
| `network_metrics_year.csv` | state × year | `degree`, `strength` (weighted degree), `strength_share`, `network_density`, `network_total_weight` |
| `graphs/crink_<year>.graphml` / `.json` | yearly weighted graph | For Gephi, R/igraph or NetworkX. `crink_all_years` pools the whole period. |

**Flow, not stock.** The panel counts events in the year they occur. A treaty in force affects later years, but it is not re-counted in them. If a stock measure is needed, build it from `tie_type == "treaty_in_force"` events.

---

## 8. Known limitations (v0.1)

- **Selection.** The seed is weighted toward events covered in English-language media and Western government disclosures. Expect gaps in Chinese–Iranian and Iranian–North Korean ties, which get the least coverage.
- **Multilateral inflation.** About 70–80% of China's coded dyad-rows with Russia and Iran come from multilateral events, such as trilateral exercises and joint UNSC action. Analyses should report results with and without multilateral events.
- **Single coder.** Inter-coder reliability has not been measured yet. The protocol in `CONTRIBUTING.md` is designed so a second coder can double-code a sample and report Krippendorff's α on `intensity` and `verification`.
