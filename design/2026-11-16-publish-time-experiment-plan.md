# Publish-Time Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Schedule each upload to go public at a rotating weekday × time-of-day slot, record the slot, and report per-slot results from YouTube Analytics.

**Architecture:** A pure `shorts/slots.py` picks tomorrow's least-used window from `published.json` history. `publish.upload` gains a `publish_at`, `store.mark_published` records the slot, and `pipeline.py` wires them together behind a `--no-schedule` opt-out. A separate `shorts/report.py` (pure table builder + thin Analytics API fetch) backs `pipeline.py report`.

**Tech Stack:** Python 3.12, `zoneinfo`, google-api-python-client (YouTube Data v3, YouTube Analytics v2), pytest.

**Spec:** `design/2026-11-16-publish-time-experiment-design.md`

## Global Constraints

- Time zone: `America/New_York`, handled with `zoneinfo` (DST-correct).
- Windows: `07:00`, `12:00`, `17:00`, `20:00` local; 7 weekdays → 28 cells.
- A video is scheduled for **tomorrow** (local date), and never less than **10 hours** after the run.
- Upload body: `privacyStatus: "private"` plus `publishAt` as RFC 3339 UTC (`YYYY-MM-DDTHH:MM:SSZ`).
- `published.json` entries gain `publish_at` (ISO, UTC), `weekday` (`"Mon"`…`"Sun"`), `window` (`"HH:MM"`).
- The upload token keeps only `youtube.upload`. Analytics uses a separate secret `YT_ANALYTICS_REFRESH_TOKEN` with `yt-analytics.readonly` + `youtube.readonly`.
- Daily cron stays `17 15 * * *`.
- No new dependencies.

## Review Focus

1. **Late manual trigger:** a run at 23:30 ET must not schedule for 07:00 next morning (7.5h); it moves to the next qualifying slot. Test in Task 1.
2. **Legacy/unscheduled entries:** `published.json` entries without `weekday`/`window` (two-sum today, `--no-schedule` uploads) must be ignored when counting, not crash. Test in Task 1.
3. **DST change day:** a 07:00 slot on 2027-03-14 (spring forward) must be 11:00Z, and on 2026-11-01 (fall back) 12:00Z. Test in Task 1.
4. **Too-recent videos in the report:** Analytics returns no rows for a video published hours ago; the table shows `–`, not a crash. Test in Task 3.
5. **Missing analytics secret:** `report` without `YT_ANALYTICS_REFRESH_TOKEN` exits with a message naming the secret and the auth command. Test in Task 3.

---

### Task 1: Slot picker

**Files:**
- Create: `shorts/slots.py`
- Test: `tests/test_slots.py`

**Interfaces:**
- Produces: `TZ: ZoneInfo`, `WINDOWS: list[str] = ["07:00", "12:00", "17:00", "20:00"]`, `MIN_LEAD = timedelta(hours=10)`,
  `class Slot(NamedTuple): publish_at: datetime  # tz-aware, TZ; weekday: str; window: str`,
  `pick_slot(now: datetime, history: dict, rng: random.Random) -> Slot`.

- [ ] **Step 1: Write the failing tests** in `tests/test_slots.py`:
  - `test_picks_tomorrow`: `now = 2026-11-16 10:17 ET` (a Monday), empty history → `slot.publish_at.date() == 2026-11-17`, `slot.weekday == "Tue"`, `slot.window in WINDOWS`.
  - `test_least_used_window_wins`: history has Tue entries for `07:00`, `12:00`, `17:00` → `slot.window == "20:00"`.
  - `test_ignores_entries_without_slot`: history `{"two-sum": {"video_id": "x", "at": "..."}}` plus Tue entries for three windows → still `"20:00"`, no exception.
  - `test_min_lead_respected`: `now = 2026-11-16 23:30 ET`, history makes `07:00` the only least-used Tue window → `slot.publish_at - now >= MIN_LEAD`.
  - `test_dst_spring_forward`: `now = 2027-03-13 10:00 ET`, history forcing `07:00` → `slot.publish_at.astimezone(UTC).hour == 11`.
  - `test_dst_fall_back`: `now = 2026-10-31 10:00 ET`, history forcing `07:00` → UTC hour `12`.
  - `test_deterministic_with_seed`: same `now`, empty history, `random.Random(1)` twice → equal slots.

- [ ] **Step 2: Run** `pytest tests/test_slots.py -v` → FAIL (`ModuleNotFoundError: shorts.slots`).

- [ ] **Step 3: Implement `pick_slot`.** Count history entries by `(weekday, window)` (skip entries missing either key). Starting at tomorrow, for each day: candidates = windows whose local datetime ≥ `now + MIN_LEAD`; if any, pick the minimum count, break ties with `rng.choice` over the sorted tied windows, return. Otherwise try the next day. Build local datetimes with `datetime.combine(date, time, tzinfo=TZ)`; weekday from `strftime("%a")`.

- [ ] **Step 4: Run** `pytest tests/test_slots.py -v` → 7 passed.

- [ ] **Step 5: Commit** `git add shorts/slots.py tests/test_slots.py && git commit -m "Add publish slot picker"`

### Task 2: Scheduled upload, recording and wiring

**Files:**
- Modify: `shorts/publish.py` (`upload`)
- Modify: `shorts/store.py` (`mark_published`)
- Modify: `pipeline.py` (`run`, `main`)
- Modify: `.github/workflows/daily-short.yml`
- Modify: `README.md` (pipeline diagram line and "API uploads start private" note)
- Test: `tests/test_schedule.py`

**Interfaces:**
- Consumes: `pick_slot`, `Slot`, `TZ` from Task 1.
- Produces: `upload(path, meta, privacy="private", publish_at: datetime | None = None) -> str`;
  `upload_body(meta, privacy: str, publish_at: datetime | None) -> dict` (split out of `upload` so it is testable without network);
  `mark_published(slug, video_id, slot: Slot | None = None)`;
  `run(problem, upload=False, quality="final", schedule=True)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_schedule.py`:
  - `test_body_has_publish_at_utc`: `publish_at = 2026-11-17 20:00 ET` → `body["status"]["publishAt"] == "2026-11-18T01:00:00Z"` and `body["status"]["privacyStatus"] == "private"`.
  - `test_body_without_publish_at`: `publish_at=None` → `"publishAt" not in body["status"]`.
  - `test_mark_published_records_slot`: with `store.PUBLISHED` monkeypatched to a `tmp_path` file, `mark_published("x", "vid", slot)` → entry has `publish_at == "2026-11-18T01:00:00+00:00"`, `weekday == "Tue"`, `window == "20:00"`.
  - `test_mark_published_without_slot`: no slot → entry has only `video_id` and `at` (unchanged format).

- [ ] **Step 2: Run** `pytest tests/test_schedule.py -v` → FAIL (`upload_body` missing / unexpected `slot` kwarg).

- [ ] **Step 3: Implement.** `upload_body` holds today's body plus `publishAt` (UTC, `strftime("%Y-%m-%dT%H:%M:%SZ")`) when given; `upload` calls it. `mark_published` adds the three fields when `slot` is given.
  In `pipeline.run`, when `upload and schedule`: `slot = pick_slot(datetime.now(TZ), store.published(), random.Random())`, pass `slot.publish_at` to upload and `slot` to `mark_published`, and notify with exactly:
  `🎬 {spec.title} goes public {slot.weekday} {publish_at:%-I%p} ET ({publish_at:%b %-d}) unless you cancel: {url}` (lowercase `am/pm`, e.g. `Tue 8pm ET (Nov 17)`). Without schedule, keep today's message.
  `main`: add `--no-schedule` (`store_true`), pass `schedule=not a.no_schedule` to both `run` call sites.
  Workflow: add input `schedule` (boolean, default true, description "Schedule a publish time (off = stay private)"); env `SCHEDULE: ${{ github.event_name == 'schedule' || inputs.schedule }}`; append `--no-schedule` to `FLAGS` when `SCHEDULE` is not `true`.
  README: update the diagram's "upload as PRIVATE" stage to "upload private + scheduled publish" and add one bullet under "Things to know" saying videos go public at their slot unless cancelled in Studio, and `--no-schedule` keeps them private.

- [ ] **Step 4: Run** `pytest -q` → all pass (9 existing + 7 + 4). Also `python pipeline.py --help` shows `--no-schedule`.

- [ ] **Step 5: Commit** `git add shorts/publish.py shorts/store.py pipeline.py .github/workflows/daily-short.yml README.md tests/test_schedule.py && git commit -m "Schedule uploads into rotating publish slots"`

### Task 3: Results report

**Files:**
- Create: `shorts/report.py`
- Modify: `pipeline.py` (`report` command; `slug` stays optional)
- Modify: `scripts/youtube_auth.py` (add `--analytics` flag)
- Modify: `README.md` (one "Results" paragraph)
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `published.json` entries from Task 2; `WINDOWS` from Task 1.
- Produces: `fetch_stats(entries: dict) -> dict[str, dict]` (slug → `{"views_48h", "views_7d", "avg_view_pct", "subs"}`, values `None` when no data);
  `build_table(entries: dict, stats: dict) -> str`; `main()` used by `pipeline.py report`.

- [ ] **Step 1: Write the failing tests** in `tests/test_report.py`:
  - `test_table_groups_by_cell`: two Tue `20:00` entries with `views_7d` 100 and 300 and one Wed `07:00` with 50 → table row `Tue` has `200` (mean) under `20:00`, `n=2`; `Wed` row has `50` under `07:00`.
  - `test_missing_stats_show_dash`: entry whose stats are all `None` → its cell shows `–`, no exception.
  - `test_unscheduled_entries_skipped`: entry without `weekday` is absent from the table.
  - `test_missing_secret_message`: with `YT_ANALYTICS_REFRESH_TOKEN` unset, `report.main()` raises `SystemExit` whose message contains `YT_ANALYTICS_REFRESH_TOKEN` and `scripts/youtube_auth.py --analytics`.

- [ ] **Step 2: Run** `pytest tests/test_report.py -v` → FAIL (`ModuleNotFoundError: shorts.report`).

- [ ] **Step 3: Implement.** `build_table`: rows `Mon`…`Sun`, columns `WINDOWS`, each cell `mean views_7d (n=k)` or `–`; below it, a per-video list (slug, slot, views_48h, views_7d, avg view %, subs).
  `fetch_stats`: credentials like `publish.upload` but from `YT_ANALYTICS_REFRESH_TOKEN` with scopes `yt-analytics.readonly`, `youtube.readonly`; one `youtubeAnalytics.reports().query(ids="channel==MINE", metrics="views,averageViewPercentage,subscribersGained", filters=f"video=={id}", startDate=d0, endDate=d1)` per window, where `d0` is the local publish date, the 48h window ends `d0 + 1 day` and the 7-day window ends `d0 + 6 days`. Skip a window whose end date is after today (→ `None`). Empty `rows` → `None`.
  `main`: check the secret first (message above), load `store.published()`, print `build_table`.
  `youtube_auth.py --analytics`: use the two analytics scopes and print `YT_ANALYTICS_REFRESH_TOKEN=` instead of the three upload values.
  README "Results": run `python pipeline.py report`; Analytics data lags 2–3 days.

- [ ] **Step 4: Run** `pytest -q` → all pass; `python pipeline.py report` with the secret unset prints the missing-secret message.

- [ ] **Step 5: Commit** `git add shorts/report.py pipeline.py scripts/youtube_auth.py README.md tests/test_report.py && git commit -m "Add publish-time results report"`
