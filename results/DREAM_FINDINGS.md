# Dream-symbol vs. "dream meaning" baseline: eyeball pass

**Status: exploratory pattern description, not evidence.** Same discipline as
the rest of the repo — no null model, no FDR, no event-correlation testing in
this pass (that's a separate question from what's asked here: *does a symbol's
share of dream-interpretation search shift over time at all*).

**Partial data: 6 of 11 symbols pulled** (spider, snake, falling_teeth, flood,
water, baby). Fetch was stopped partway through at your request; money,
pregnant, fish, cat, death remain — `python fetch_dream_trends.py` resumes
cleanly (per-query caching) whenever you want the rest.

## Method (and two real problems found + fixed along the way)

Each `"<symbol> dream meaning"` query is meant to be a cleaner proxy than a
bare mythic word — almost nobody searches "spider dream meaning" for a reason
other than an actual dream, so this channel should dodge the brand/media
pollution that undermined the top-down symbol clusters (dragon = Game of
Thrones, etc). Compare each symbol's series to the generic **"dream meaning"**
baseline so a rise just riding the whole genre's growth doesn't get mistaken
for a symbol-specific spike.

**Problem 1 — scale-crowding (found and fixed).** The first attempt batched
each symbol together with the baseline in one Trends request so they'd share a
0–100 scale (Trends caps comparisons at 5 terms). But "dream meaning" has far
higher volume than any single symbol phrase, so Trends normalizes the whole
request to the loudest term and floors the rare ones — "flood dream meaning"
came back as a literal, flat zero for all 22 years. Confirmed via direct
Google Trends lookup that this was a batching artifact, not a real absence of
signal. **Fix:** fetch every query — baseline and each symbol — independently,
each getting its own full-resolution 0–100 scale, then divide the two
independently-normalized series. That ratio's absolute height isn't
comparable across symbols, but that's fine: we only ever z-score a symbol's
ratio against *its own* history, which is invariant to each series' own scale
factor.

**Problem 2 — the query genre itself didn't exist yet (found and handled).**
Even fetched alone, every symbol shows long literal-zero runs in the mid-2000s
(spider: 94% zero months 2004–2009; flood's last zero month is as late as
2012-04). This is real: "`<symbol> dream meaning`" as an exact-phrase search
pattern is largely a product of 2010s-era SEO dream-interpretation content —
it didn't exist as common search behavior before then. Z-scoring across that
regime change manufactures fake "co-spikes" (a flat-zero run meeting real data
reads as a huge, identical deviation for months at a stretch — exactly what
the first pass showed). **Fix:** deviation detection is restricted to
2013-01–present, with margin past every symbol's last recorded zero month. The
small-multiples plot still shows full 2004-present history with the excluded
region shaded, so the emergence is visible rather than hidden.

**A third thing worth flagging, not fixed:** Google Trends' most recent ~2–3
months are provisional and get revised as more data arrives. Confirmed here —
in 2026-05/06 *both* "water dream meaning" and the baseline itself spike to
~100 together, an edge effect of pulling up to "today," not a content signal.
The last 3 months are trimmed from deviation detection for this reason.

## What the data actually shows (results/dream_symbols_ratio.png, results/dream_symbols_heatmap.png)

The dominant shape here is **slow multi-year drift in relative share**, not
sharp isolated spikes — a different kind of pattern than the top-down pass's
event-linked-rise hypothesis, and notably *not* yet checked against
`data/events.csv` in this pass.

- **Teeth falling** ran hot (above its own norm) through 2013–2018, then had a
  multi-year *cold* stretch 2019–2022, warming again recently. A slow regime
  shift, not a spike.
- **Snake** shows a gradual, sustained warming drift starting ~2017, staying
  more consistently above-norm through 2020–2026.
- **Water** was cold 2013–2015, then gradually warmed, and is sharply hot
  right at the (reliable, non-edge) end of the series — the raw numbers back
  this up as a real gradual rise from Aug 2025 (ratio-relevant value 57) to
  April 2026 (72) against a much flatter baseline, distinct from the trimmed
  May/June instability spike.
- **Spider** was hot 2013–2015, then slowly declined into a cold stretch
  2020–2023.
- **Baby** and **Flood** are noisier month-to-month with no clear multi-year
  drift — more scattered individual hot/cold months than a trend.

No symbol shows the sharp, isolated "spike right before a big news date" shape
the original top-down hunt was looking for. What's here instead is closer to
slow-moving background drift in what people dream about (or at least look up),
on a timescale of years, not weeks.

## Honest caveats

1. **Only 6/11 symbols so far** — money, pregnant, fish, cat, death still need
   pulling before any cross-symbol picture is complete.
2. **No event-correlation check yet.** This pass only asked "did a symbol's
   own share move over time" — it deliberately didn't cross-reference against
   `data/events.csv`. Doing that honestly would need the same discipline as
   the rest of the repo (a null model), not eyeballing.
3. **The "reliable window" cutoffs (2013-01 start, 3-month end trim) are
   judgment calls**, chosen from the specific data pulled, not a universal
   constant. If you add more symbols and one has its own later last-zero
   month, this cutoff should move for that symbol too.
4. **The 2025-26 water rise is genuinely recent** — worth re-checking again in
   a few months once those endpoints stop being "provisional" in Trends' own
   data.
