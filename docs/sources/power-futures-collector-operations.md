# Power futures collector: operations and data quality

2 October 2026. Companion to `power-futures-data-access.md`, which covers what the two sources are and what they publish. This one covers running the collector, what its outputs do and do not guarantee, and the defects found in its first fortnight.

Tool location: `C:\Users\Admin\Documents\KTH\iPoY\PowerFuturesCollector`

**Current state as of 2 October 2026:** 49,341 observations, 6 August to 2 October, 34 zones. EEX complete with no gaps and 1,195 of 1,195 instruments collected. Euronext complete except five permanently lost days, listed below. All data-quality invariants verified clean.

---

## The one fact that governs everything else

The two sources fail differently when a day is missed, and the difference is not symmetric.

**EEX serves a rolling window of roughly 33 trading days.** Every run requests a 45-day window and upserts, so a day nobody collected is backfilled by the next run. Downtime of up to about six weeks costs nothing. One sweep per day is sufficient, and more would be discourteous to a public endpoint for no gain, since a sweep is about 1,200 requests and 20 minutes.

**Euronext serves only the current snapshot.** There is no date parameter and no history. A trading day nobody collected is gone from that source permanently. The sweep is 14 requests and about 20 seconds.

This is why the schedule is split into two Windows tasks rather than one. EEX runs once daily at 19:30, after both exchanges publish settlement. Euronext runs every two hours from 07:00, so that any day on which the machine is switched on at all gets captured.

Five Euronext days were lost before this was understood: 23 and 24 September, and 29 and 30 September and 1 October 2026. The cause was mundane. The machine was not awake at 19:30, and `-StartWhenAvailable` fired the task late or not at all. The run times drifted from 19:47 to 20:08, then 23:52, 00:05 and 00:29, which is the signature of that setting rather than of a failing task.

What those five days actually cost is less than it first appears. EEX covers the same Nordic zones, including the Nordic system price, and those dates sit inside its recoverable window, so the price levels survive and the EPAD basis can be derived as EEX zonal minus EEX Nordic. What is genuinely gone is the Euronext-specific layer: traded volume and open interest on the EPAD contracts as they trade there, and the Lithuanian EPAD, which EEX does not carry in the configured area set. For the return-distribution work this costs nothing. For the liquidity metrics Flower flagged it is five days of thinner evidence.

---

## Runbook

All commands are run from the tool folder. Note that PowerShell does not execute scripts from the current directory without the `.\` prefix, so `run_collector.bat` fails where `.\run_collector.bat` succeeds. This has already cost one backfill that appeared to run and did not.

```
.\setup.bat                                      one-time: venv, dependencies, tests, reachability
powershell -ExecutionPolicy Bypass -File .\install_task.ps1     register the two scheduled tasks
.\run_collector.bat                              collect now (safe to repeat; re-collection is idempotent)

.venv\Scripts\python -m powerfutures status       row counts, date span, per-source run health
.venv\Scripts\python -m powerfutures gaps         trading days absent, and whether they are recoverable
.venv\Scripts\python -m powerfutures export       whole archive as one long CSV
.venv\Scripts\python -m powerfutures selftest     check both endpoints respond
.venv\Scripts\python diagnose_eex.py              why EEX is refusing, if it ever does
```

Checking the schedule itself:

```
Get-ScheduledTask 'iPoY Power Futures Collector*' | Select TaskName, State
Get-ScheduledTaskInfo 'iPoY Power Futures Collector' | Select LastRunTime, NextRunTime, LastTaskResult
```

`LastTaskResult` of 0 means the last run succeeded and 267011 means it has not run yet.

Removing rows that should never have been recorded, dry run first:

```
.venv\Scripts\python -m powerfutures repair --source EURONEXT --trade-date 1970-01-01
.venv\Scripts\python -m powerfutures repair --source EURONEXT --trade-date 1970-01-01 --apply
```

`repair` backs the database up first, clears the revision log for the rows it removes, and accepts `--source`, `--trade-date` and `--delivery-label` in any combination.

---

## What the archive guarantees

Observations are upserted on an identity that excludes the values and the retrieval time, so re-collecting a day is idempotent and a genuine exchange revision updates the row rather than duplicating it. Every superseded value is kept in `observation_history`, so a revision is visible rather than silent.

The dated CSV snapshots under `data\raw\` are never rewritten. If a figure in the analysis is ever questioned, the file that produced it is still on disk exactly as fetched.

The `runs` table records every collection attempt with `status` of `ok`, `partial` or `failed`, plus `units_requested` and `units_failed`. **A `partial` run deserves attention out of proportion to its name.** If a zone's instruments failed, that zone looks untraded rather than uncollected, and nothing downstream distinguishes the two. `status` prints this and flags anything that is not `ok`.

A missing value is stored as null, never as zero. The distinction carries weight here: a contract that did not trade has no volume, which is not the same as a contract that traded zero.

---

## Defects found, and what each one changed

Five defects surfaced in the first fortnight. **Four of the five were silent**, in the sense that the run reported success, the row counts looked plausible, and only a deliberate check exposed them. That pattern is the main lesson rather than any individual bug.

**Connection leak locking the archive.** `with sqlite3.connect(...) as conn` commits the transaction but does not close the connection. Linux tolerates the open handle; Windows locks the file. Symptom in testing was a temporary directory refusing to delete; the production symptom would have been the archive unreadable from pandas while a collection was running. Every database call now closes in a `finally`, and a test counts opens against closes rather than relying on the filesystem to object.

**Rate limiting losing 45% of the universe, reported as success.** Six unthrottled workers lost 498 of 1,097 EEX instruments to HTTP 429. Six zones went to zero, including Finland, and SE3 kept 2 instruments out of 21. Each failure was caught per instrument and logged, so the run recorded `ok` with 19,168 rows. Requests are now paced by a throttle shared across threads, a 429 backs off the whole throttle rather than the one thread that hit it, whatever still fails gets a slower single-threaded retry pass, and any residue is recorded as `partial`.

**A date fallback splitting one curve across two sessions.** The deeper Euronext ranks return the table without an "Updated" stamp, and substituting today's date filed Cal-2033 through Cal-2036 on a Sunday while Cal-2027 through Cal-2032 sat correctly on the Friday. The sweep's single date is now applied to the whole sweep, and a sweep producing more than one date is refused.

**A label collision destroying 64 observations a day.** EEX publishes no season name for the GB season contracts, so Summer-2027 and Winter-2027 both derived the label `Season-2027`. Identical short code, product, zone and label meant an identical observation identity, so the two contracts overwrote each other every run and each overwrite was logged as a price revision the exchange never made. The 128 "revisions" in the archive were entirely this artefact. Season labels now come from the maturity month, every observation stores the exchange's own maturity key as provenance, and `upsert` raises rather than merging when one identity covers two maturities.

**A placeholder timestamp accepted as a session.** When the Euronext block has nothing live to report it stamps itself "Updated 01/01/1970 01:00 CET". The guard added for the previous defect rejected a missing stamp but accepted an absurd one, so 136 real observations were filed under the Unix epoch. Implausible stamps are now rejected in the parser, and an independent archive-level guard refuses any trade date outside a plausible window.

The through-line is that every one of these corrupted or lost data while leaving the archive looking complete and internally consistent. **The framework's own estimators deserve the same treatment: an assertion on expected coverage will earn its keep more than an inspection of the numbers.** Each defect above is now pinned by a test, 24 in total, and three of those tests were verified to fail against the original code rather than merely passing alongside the fix.

---

## The 2 October 2026 remediation run

The first run after all five fixes were in place, recorded because it is the baseline every later run should be compared against.

The three stale GB season label groups were removed first, 64 observations each, 192 in total. The `Season-2027` removal also cleared 128 revision log entries, which confirms those "revisions" were the collision artefact and nothing else: no other label group carried any.

The EEX sweep then collected **1,195 of 1,195 instruments with zero failures**, producing 39,435 observations in 20 minutes. This is the throttle fix holding at a larger scope than the one it was written for, which matters because the universe had grown in the meantime.

Euronext reported 189 observations all dated 2 October, with the stamp recorded as `2026-10-02T12:46`. Zero were new, because the two-hourly task had already captured that day, which is the first direct evidence that the new schedule is doing its job.

**The implausible-stamp guard fired in production during this run.** At rank 11 the log shows `Euronext stamp 1970-01-01 is implausible (today is 2026-10-02); treating as absent`. So the placeholder appears reliably at the end of the curve walk, and the guard now catches it rather than filing another 136 epoch-dated rows. The rank progression also exhausted cleanly at 11 of a configured 14, so `euronext_max_rank` has adequate margin.

Invariants verified clean afterwards: zero stale `Season-*` rows, zero identities carrying two maturities, zero orphaned history entries, GB seasons showing only Summer and Winter labels, and `source_timestamp` populated on every Euronext row.

### The instrument universe grows, and that broke a check

EEX went from 1,097 to 1,195 power futures instruments in scope between 20 September and 2 October, with the full catalogue growing from 7,135 to 7,856. Contracts roll, so new maturities appear continuously. The median EEX row count per trade date rose from 1,103 to 1,195 over the same fortnight.

This quietly invalidated the completeness heuristic in `gaps`, which compared each date's row count against the median of the whole archive. Over a nine-month archive growing from 1,100 to 2,000 instruments, a global median falsely flags 59 of 180 dates as partial while the correct answer is none. A check that cries wolf is a check nobody reads, so each date is now judged against the median of its eleven nearest neighbours instead, which tracks the growth. The behaviour in both directions is pinned by a test.

The general point is worth carrying into the framework: **any completeness or outlier rule must be stated relative to the universe at that time, not to the archive as a whole.** The same trap waits in any per-zone instrument-count normalisation.

---

## Validation that passed

The strongest check available is that the Nordic zones are covered twice over, by EEX directly and by Euronext as system price plus EPAD basis, through entirely separate endpoints, parsers and unit conventions.

Across 12 zones and two tenors, all 24 comparisons of EEX zonal settlement against Euronext system price plus EPAD agreed within 1.09 EUR/MWh, and most within 0.5, on prices spanning 29 to 168 EUR/MWh. SE1 was the loosest at about 1.0, consistent with it being the thinnest Swedish zone. That residual is what two venues settling at slightly different times would produce, not an error.

What it validates is everything underneath: all 12 EPAD to bidding-zone mappings, negative EPAD price handling, delivery-label alignment across sources, and trade-date alignment. A single mis-mapped EPAD would have shown tens of euros.

Separately, EEX open interest in lots multiplied by the hours in the delivery period equals open interest in MWh, which is what establishes which column carries which unit. A test asserts that relationship, so a field swap upstream fails the suite rather than quietly mixing units in the archive.

This cross-check is worth keeping as a standing data-quality monitor rather than deduplicating the redundancy away.

---

## Reading the revision log

After the 2 October run the archive holds 738 logged revisions, and they are not all the same kind of thing.

The EEX revisions are small and numerous: quarters averaging 0.87 EUR/MWh of movement, months 1.58, years 0.33. Those are genuine settlement revisions and need no action.

The large Euronext revisions are a different mechanism, and understanding it matters before using Euronext prices.

```
2026-09-21  NSBD  2026-09-22   107.50 -> 152.32   corrected at 18:06
2026-09-21  NSBD  2026-09-23   107.50 -> 150.00   corrected at 18:06
2026-09-25  NSBW  W41-2026     104.58 -> 130.00   corrected at 22:11
```

The repeated 107.50 across different delivery dates is a pre-settlement carry-forward value, replaced by the real settlement once a later run caught it. This is the two-hourly schedule working as intended: an early reading is superseded rather than lost. It is also why `source_timestamp` exists. **An observation whose `source_timestamp` falls before roughly 17:00 CET may hold the previous session's settlement, and analysis that cares about exact daily settlement should filter on that column rather than assume.**

---

## Caveats to carry into the framework

**Exchange-cleared volume is not total market liquidity.** A large share of European power hedging is OTC and invisible in both sources. Comparing a heavily exchange-traded market such as Germany against one where bilateral trading dominates, and reading the difference as a liquidity gap rather than a market structure difference, would be a mistake worth guarding against explicitly.

**EEX publishes roughly a day behind Euronext.** Confirmed again on 2 October: Euronext held that day's session while EEX's latest was 1 October. The rolling window means nothing is lost, but the archive runs about a day behind on the larger source. Irrelevant for historical distribution work; it would matter only if same-day figures were ever wanted.

**Euronext settlement timing needs watching.** See the revision log section above. `source_timestamp` is the column that distinguishes a provisional reading from a final one.

**The instrument universe is not constant.** Any count-based completeness or normalisation rule must be relative to the universe at that date.

**Neither source exposes intraday liquidity or order book depth.** The intraday liquidity indicator Flower named still needs a different source.

---

## Open operational risk

The collector depends on one laptop being awake. Two-hourly Euronext polling makes a single missed evening harmless, but a stretch of days with the machine off still loses Euronext days permanently, and those are the only genuinely unrecoverable losses in the system.

The durable answer is to run the Euronext collector somewhere always on. Fourteen requests every two hours is trivial to host, and a small cloud instance or a scheduled CI job would remove the dependency entirely. This is worth deciding before the archive accumulates value that cannot be reconstructed, since the cost of the decision rises with every week of history held.

---

## Licensing reminder

EEX permits infrequent distribution of insubstantial parts of its data and requires express permission for systematic republication of substantial amounts. Private use within the team and with Flower is fine; publishing the archive or committing `data\` to a public repository is not. Published outputs should be derived statistics rather than tables of raw daily settlement prices. `NOTICE.md` in the tool folder carries the detail, the reasoning behind the request headers the collector sends, and a suggested citation.
