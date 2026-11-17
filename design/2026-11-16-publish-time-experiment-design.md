# Publish-time experiment

## Why
Learn which days and times of day get the best results for these Shorts, instead of
publishing everything at one fixed time.

## Approaches
- **A. Pipeline schedules the publish (chosen).** Upload private with `status.publishAt` set to an
  assigned slot; the video goes public at that slot unless Mark cancels it in Studio. Exact timing,
  so the data is clean. Trade-off: "nothing goes public without you" becomes "public unless you stop it".
- B. Mark publishes by hand at a suggested slot. Keeps the manual gate, but timing drifts with when
  he gets to it, which muddies the data.
- Varying the cron only (rejected): upload time isn't publish time, so it tests nothing.

## Design
- **Slots** (my call): four windows in America/New_York, 07:00, 12:00, 17:00 and 20:00, crossed with
  the 7 weekdays = 28 cells. DST handled by `zoneinfo`.
- **Assignment** (my call): each run schedules its video for **tomorrow**, in tomorrow's window that has
  been used least so far on that weekday (ties broken randomly). Every cell gets filled before any
  repeats, and there are always 10+ hours to review before the video goes live.
- **Upload**: `privacyStatus: private` + `publishAt` (UTC). `published.json` records `publish_at`,
  `weekday` and `window` next to `video_id`.
- **Ping**: "🎬 <title> goes public Tue 20:00 ET unless you cancel: <studio link>".
- **Opt-out**: `--no-schedule` (and a workflow input) uploads plain private, as today.
- **Cron**: unchanged (10:17 ET). It only controls when the private upload lands.
- **Results**: a `pipeline.py report` command pulls views, average view % and subscribers gained per
  video from the YouTube Analytics API at 48h and 7 days after publish, then prints a weekday × window
  table. It needs a one-time read-only sign-in (`yt-analytics.readonly` + `youtube.readonly`) stored as
  a new secret, `YT_ANALYTICS_REFRESH_TOKEN`, so the upload token keeps its single permission.

## Constraints
- Until Google audits the API project, API uploads are locked private, so `publishAt` won't take effect.
  The code ships now; the experiment starts once the audit passes.
- One video a day means about one data point per cell per month. Treat results as a rough signal.

## Non-goals
- Changing what gets made, or how often. Statistical modelling beyond a per-cell table.

## Left to the builder
- Retries and timeouts for the Analytics API calls; output format of `report`.
