# Jung & Big Data

An exploratory inquiry into whether **Jungian archetypal symbolism**, as
expressed through collective search behaviour (Google Trends), shows any
**lead relationship** with major world events.

## The idea (and its honest limits)

The working conjecture is that the collective unconscious processes far more
information than we consciously register, and expresses emerging tensions
through archetypal symbols — in dreams, art, and (the assumption here) in what
people search for. If so, interest in certain symbols might rise *before* the
events they seem to prefigure.

This project takes that seriously as a thing to **look at**, while being blunt
about what it is not:

- **It is not proof of anything.** It is pattern observation.
- **The central danger is apophenia** — seeing meaning in noise. That is
  literally the phenomenon under study, so the method is built to fight it.
- **Symbolic meaning is observer-dependent** (as Jung held). We only claim an
  *intersubjective, quantifiable-with-limitations* slice of it, encoded
  explicitly in a human-readable ontology you can argue with.
- **The boring confound is news coverage.** When an event brews, media covers
  it and people search consciously. That is information flow, not the
  unconscious. So we separate two channels and only care when the symbolic one
  adds something the literal one doesn't.

## Getting the data (Google Trends is blocked in the cloud env)

This repo runs in a managed environment whose egress policy **blocks
`trends.google.com`**, so automated pulls (`pytrends`) fail with a proxy 403.
The pattern hunt therefore uses a **manual export** flow:

```bash
python make_export_links.py          # writes data/trends_export/EXPORT_LINKS.md
```

Open each generated link, click the download (↓) icon on the **Interest over
time** card, and save the CSV into `data/trends_export/` under the filename the
table gives (e.g. `serpent_snake.csv`). Then:

```bash
python analyze.py                    # imports whatever CSVs are present -> results/
```

`analyze.py` tells you which clusters still need exporting, so you can do them a
few at a time. The tracked symbols live in **`symbols.yaml`** — plain query
strings you can edit and re-export.

*(To automate instead: recreate the environment with a network policy that
allows `trends.google.com`; then a live `pytrends` fetcher can replace the
manual step.)*

## Brand archetypes in markets (live stock withdrawal)

The same archetype idea has a marketing-world descendant: modern brands are
deliberately built on one of the **twelve Jungian brand archetypes** (Mark &
Pearson, *The Hero and the Outlaw*) — Hero, Outlaw, Magician, Sage, Ruler,
Lover, and so on. So a companion question is whether a brand's archetype tracks
its **stock price**.

Unlike Trends, live market data *does* come down in this environment — prices
are withdrawn straight from Yahoo Finance (no API key, no extra library):

```bash
python withdraw_stocks.py                # 2y daily prices for every tracked brand
python withdraw_stocks.py --range 5y     # longer window (6mo, 1y, 2y, 5y, max)
```

This pulls each brand's adjusted daily close, writes one CSV per ticker into
`data/stocks/`, prints per-brand and per-archetype window returns, and renders
`results/brand_archetype_indices.png` — an **equal-weight, rebased-to-100 stock
index per archetype**, so you can eyeball whether an archetype basket has out-
or under-performed. The brand→archetype→ticker mapping lives in **`brands.yaml`**
(edit it freely; nothing downstream hard-codes the tickers). Prices cache to
`data/cache/stocks/` keyed by the calendar day, so a same-day re-run is instant.

Same discipline as the rest of the repo: the baskets are tiny, hand-picked, and
confounded by sector — any gap is a **hypothesis, not a finding**.

## Method

**Two channels, measured the same way.**

- *Symbolic* terms — abstract/mythic expressions of archetypes
  (`ontology/archetypes.yaml`): *the flood*, *phoenix*, *mandala*, *the
  serpent*, …
- *Literal* controls — the on-the-nose things people consciously search per
  event category (`ontology/literal_controls.yaml`): *recession*, *pandemic*,
  *invasion*, … These represent the news-coverage channel the symbolic channel
  must beat to be interesting.
- *Placebo* terms — neutral words with no archetypal charge
  (`data/placebo_terms.txt`): *chair*, *spoon*, … If these light up as much as
  symbolic terms, we're measuring artifacts.

**Pre-event lift.** For each term × event we fetch ~15 months of weekly Trends
around the event and compute a standardized *lift*:

```
lift_z = (mean(pre-event window, weeks -12..-1) - mean(baseline, weeks -52..-13))
         / std(baseline)
```

i.e. *did interest run hotter than usual in the quarter before the event?*

**Null models (the discipline).** A broad scan will always surface some large
lifts by chance. Each term gets an **empirical null**: many random "placebo
dates" far from any real event, run through the identical statistic. Because it
reuses the term's own series, this absorbs its seasonality and autocorrelation.
The null is built at the **same scale** as the observed statistic (a bootstrap
of the K-event mean, not single dates). Across all terms we then apply
**Benjamini-Hochberg FDR** so "significant" accounts for how many terms we
looked at.

**Framing.** A term surviving FDR here is a **hypothesis for a focused,
pre-registered follow-up**, not a finding. The broad scan is a
hypothesis-*generator*.

## Layout

Active pattern-hunt path (start here):

```
symbols.yaml                    the tracked symbol clusters (edit the queries here)
make_export_links.py            -> data/trends_export/EXPORT_LINKS.md click-ready links
data/trends_export/             drop your Google Trends CSV exports here (<key>.csv)
data/events.csv                 dated, categorized world events (2004+, Trends' floor)
src/symbols.py                  cluster loader + explore-URL builder
src/trends_import.py            reads Google Trends CSV exports into tidy frames
src/visualize.py                small-multiple series + event overlays + sun/moon ratio
analyze.py                      CLI: import exports -> results/*.png
```

Brand-archetypes-in-markets path (live, no key needed):

```
brands.yaml                     the twelve brand archetypes -> tickers (edit here)
src/brands.py                   brand loader + archetype grouping
src/stocks.py                   live Yahoo Finance provider (adjusted close, cached)
withdraw_stocks.py              CLI: pull live prices -> data/stocks/ + results/*.png
```

Optional statistical follow-up (for when a pattern looks worth pressure-testing):

```
ontology/archetypes.yaml        archetype -> symbolic search terms
ontology/literal_controls.yaml  event category -> literal control terms
data/placebo_terms.txt          neutral control terms
src/analysis.py                 standardized pre-event lift
src/nulls.py                    empirical null + Benjamini-Hochberg FDR
src/scan.py, run_scan.py        broad scan with null models (synthetic self-test)
src/trends.py                   live (pytrends, cached) + synthetic providers
```

## Usage

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Offline pipeline validation (no network). Plants a synthetic pre-event
# signal into symbolic terms at real events only -> detector should flag them:
python run_scan.py --mode synthetic --plant-signal 12

# Offline false-positive check: no planted signal -> symbolic should look no
# different from placebo, near-zero FDR hits:
python run_scan.py --mode synthetic --plant-signal 0

# Real Google Trends (unofficial, slow, rate-limited; results cache to data/cache/):
python run_scan.py --mode live --geo ""     # "" = worldwide, or e.g. US
```

Outputs land in `results/`: `scan_summary.csv`, `channel_means.csv`, and a
`pre_event_lift.png` bar chart (blue=symbolic, green=literal, red=placebo).

## Pipeline validation

The synthetic mode is a built-in self-test of the detector:

| Scenario | Symbolic mean lift | Placebo mean lift | FDR-significant terms |
|---|---|---|---|
| Signal planted at real events | **+0.51** | −0.02 | 34 (symbolic), literal/placebo correctly not flagged |
| No signal (pure null) | −0.017 | −0.016 | 1 / ~80 (≈1%, under the 10% FDR target) |

So the method detects real lead-signal and does not hallucinate it under noise —
the prerequisite for trusting anything the live scan surfaces.

## Known limitations / caveats

- Google Trends is relative & normalized, unofficial via `pytrends`, samples
  noisily, and only reaches back to 2004.
- Symbol words are **polysemous** (*shadow*, *tower*, *flood* mean many things);
  this inflates noise. Term disambiguation (topic IDs, joint terms) is future work.
- Reverse causality: events cause searches. The lead-window design mitigates but
  cannot eliminate this — aftershocks, anticipation, and slow-burn events blur
  "before" and "after".
- The archetype→term ontology is a judgment call. It is versioned precisely so
  that disagreement is visible and testable.

## Possible next steps

- Add topic-ID disambiguation to the live fetcher.
- Per-category and per-archetype aggregation (does *apocalypse* symbolism lead
  *financial* events specifically?).
- Additional symbolic corpora beyond Trends (art/film metadata, dream-report
  datasets) to triangulate the "expression" signal.
- Pre-registered confirmatory studies for any hypotheses the scan generates.
