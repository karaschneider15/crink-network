# Adding or correcting events

1. **Search before adding.** Check that the event is not already coded, for example by searching `events.csv` for the date and the dyad.
2. **Append a row** to `data/raw/events.csv` with the next free `event_id`. Never renumber existing IDs.
3. **Follow the codebook.** `CODEBOOK.md` defines `intensity` (§4) and `verification` (§5). If a case is borderline, explain your reasoning in `notes`.
4. **Write the description in your own words.** It should be one neutral sentence, with no quotes over 15 words.
5. **Validate and rebuild:**
   ```bash
   crink validate
   crink build
   pytest
   ```
6. **Open a pull request.** The title should be the event ID(s) and a short label. CI re-runs validation.

## Corrections

To correct a fact, edit the row in place and add an explanation to `notes`, for example: `2026-12-01: regraded B→A after DPRK confirmation`. Git history serves as the audit trail.

## Double-coding protocol (reliability)

A second coder receives `description` and the source URLs only, and codes `domain`, `tie_type`, `intensity` and `verification` blind. The results are compared with `scripts/reliability.py` (planned), and Krippendorff's α is reported in the release notes.
