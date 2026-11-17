# leetcode-shorts

Automated YouTube Shorts that animate LeetCode solutions in Manim, with ElevenLabs narration.

```
problems.yaml ─► spec (Claude, schema-forced) ─► verify (run code + traces) ─► render (Manim templates)
                                                                                   │
     goes public at its slot unless you cancel ◄── ping ◄── upload private + slot ◄┘
```

Each video gets at least 10 hours for review before its slot, and you can cancel it in Studio.
Claude writes **data** (narration, solution code, traced code, test
cases), never Manim code, and every spec has to pass `verify` before a frame is rendered: solutions run
against the tests in a separate process, and the animation comes from the trace of the code that
actually ran.

## Layout

```
pipeline.py               CLI: next | run | generate | verify | render
problems.yaml             publishing queue (each problem lists the templates it needs)
specs/<slug>.yaml         one spec per video (hand-written or generated, then committed)
published.json            what's been uploaded
shorts/
  spec.py                 the Spec schema (pydantic): also the tool schema Claude must fill
  generate.py             Claude -> Spec, with verification errors fed back on retry
  verify.py               runs code/tests/traces in a subprocess, checks highlights, sizes, keys
  scene.py                the Short's skeleton: hook -> problem -> approaches -> outro
  templates/              per-algorithm animation (pairs_brute, hashmap_scan, ...)
  style.py                palette + fonts: restyle every video here
  tts.py                  ElevenLabs / OpenAI / espeak, cached by line
  render.py               vertical 1080x1920 render
  publish.py              YouTube upload + webhook ping
scripts/youtube_auth.py   one-time OAuth to get a refresh token
.github/workflows/        daily run on GitHub Actions
```

## Local setup (Mac)

```bash
brew install ffmpeg pango pkg-config
brew install --cask font-inter font-dejavu
pyenv install 3.12 && pyenv local 3.12
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

```bash
python pipeline.py render two-sum --preview     # free offline voice, low-res, ~20s
export ELEVENLABS_API_KEY=... TTS_BACKEND=elevenlabs TTS_VOICE=TX3LPaxmHKxFdv7VOQHJ
python pipeline.py run two-sum                  # full quality -> out/two-sum.mp4
export ANTHROPIC_API_KEY=...
python pipeline.py generate contains-duplicate  # Claude writes + verifies specs/contains-duplicate.yaml
```

Always read a generated spec before it goes out. `verify` proves the code is right, not that the
narration is good.

## GitHub Actions setup

1. Push this repo to GitHub (public = unlimited free Actions minutes; private = 2,000/month, ~3 min per video).
2. **Settings → Secrets and variables → Actions → Secrets**:
   `ANTHROPIC_API_KEY`, `ELEVENLABS_API_KEY`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`,
   and optionally `NOTIFY_WEBHOOK_URL` (Discord webhook, Slack webhook or an n8n webhook).
3. **Variables**: `TTS_VOICE` = your ElevenLabs voice ID.
4. Get the YouTube values with `python scripts/youtube_auth.py client_secret.json` (steps in that file).
5. Test it from **Actions → daily-short → Run workflow** with upload off. The MP4 shows up as a build artifact.

After that it runs daily at 10:17 ET, uploads the next problem as private with a publish time
tomorrow, commits the spec and `published.json`, and pings you with that time. Review on your phone
in YouTube Studio, and cancel the schedule there if it shouldn't go out.

## Results

`python pipeline.py report` prints mean views after 7 days for each weekday × time slot, and a line
per video (views at 48h and 7 days, average view %, subscribers gained). It reads YouTube Analytics
with its own read-only token: run `python scripts/youtube_auth.py --analytics client_secret.json`
once and export `YT_ANALYTICS_REFRESH_TOKEN` (plus `YT_CLIENT_ID` / `YT_CLIENT_SECRET`). Analytics
lags 2-3 days, and one video a day is about one data point per slot a month, so read it as a rough
signal.

## Templates

| Template | What it draws | Hand-checked spec |
|---|---|---|
| `pairs_brute` | i/j over every pair, running best | two-sum, best-time-to-buy-and-sell-stock |
| `hashmap_scan` | one pass with a map/set drawn as chips | two-sum |
| `two_pointers` | L/R closing in, ruled-out cells fade | valid-palindrome |
| `sliding_window` | boxed window [L, R] growing/shrinking | best-time-to-buy-and-sell-stock |
| `stack` | push/pop row, green match / red mismatch | valid-parentheses |
| `binary_search` | L/M/R, discarded half fades | binary-search |

Every queued problem now has its templates, so problems without a saved spec (Contains Duplicate,
Two Sum II, Container With Most Water, Longest Substring, Rotated Sorted Array) will be written by
Claude on their turn. Read those specs before publishing.

Pointer-style templates (`two_pointers`, `sliding_window`, `stack`, `binary_search`) take the code line
to highlight from each event's `line`, so their `highlights` is `{}`. Shared readout slots: `label`,
`detail` (or `result`, in green), `best`, plus `say` / `say_bg` narration.

To add one (tree_dfs, grid_bfs, dp_table next): copy the closest template, define `REQUIRED`,
`HIGHLIGHTS`, `DOC` (what Claude reads) and `run()`. Register it in `templates/__init__.py`, add it to
`TemplateName` in `spec.py`, and hand-write one spec so you've seen it render before Claude uses it.
Trees and grids need new drawing code; the array row and pointers won't cover them.

## Things to know

- **API uploads start private.** Until Google audits your API project, uploads are locked private
  anyway. Request the audit once the channel is real.
- **Scheduled publishing.** Each upload is scheduled to go public tomorrow at a rotating weekday ×
  time slot (07:00, 12:00, 17:00, 20:00 ET; see `shorts/slots.py`), so you can learn which times work.
  It goes public at that slot unless you cancel the schedule in Studio. `--no-schedule` (or the
  workflow's `schedule` input) keeps a video private instead. In Actions, scheduling stays off until
  you set the repository variable `PUBLISH_SCHEDULE` to `on`: do that once Google's audit passes,
  since until then API uploads are locked private and the publish time would never happen.
- **ElevenLabs free tier:** API access only to premade voices, and, as far as I know, no commercial
  use. You need a paid plan before monetizing.
- **Don't let it become slop.** YouTube demonetizes mass-produced, near-identical videos. The review
  step, varied hooks (the generator is told not to reuse them) and an occasional video in your own
  voice keep it from looking like a content farm.
- **Spec code runs on the CI runner.** It runs in a child process with a timeout, which is fine for
  a throwaway runner. Don't point `verify` at specs from untrusted sources on your own machine.
