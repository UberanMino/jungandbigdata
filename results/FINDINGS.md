# Eyeball pass — live Trends pull, 2004-present

**Status: exploratory pattern *description*, not evidence.** These are visual
impressions from `results/symbols_overview.png` + `results/sun_moon_ratio.png`,
cross-checked against a crude per-event "pre-event lift" (mean of months −3..−1
before each event vs the cluster's own −12..−4 baseline, in baseline-std units).
No null model, no multiple-comparison control — that is what `src/nulls.py` /
`run_scan.py` are for. Do not read causation into anything here.

Data: all 17 clusters pulled **live** from Google Trends (worldwide, monthly,
stitched from two overlapping ~11.5yr windows). Zero manual fallbacks needed.

## The overwhelming first-order signal is *not* archetypal

In nearly every panel the dominant structure is a **secular trend** and/or
**brand / media / calendar spikes**, not a rise that leads the red event lines.
The event markers mostly do *not* line up with consistent pre-event ramps. Read
every "pre-event lift" below against that backdrop.

## Brand / pollution flags (do NOT over-read these)

These clusters are contaminated enough that their shapes are mostly telling us
about pop culture, not the collective unconscious:

- **Dragon** — Game of Thrones (2011–2019), How to Train Your Dragon (2010),
  Skyrim (2011), Dragon Ball. The high 2010–2016 plateau is the GoT/fantasy era,
  then it decays. Its *negative* mean pre-event lift is just that decay.
- **Wolf / the Beast** — GoT direwolves + **The Wolf of Wall Street** (Dec 2013)
  drives the big 2014 spike; Beauty and the Beast (2017) the next one. The
  "pre-Ebola 2014" and "pre-Sandy" bumps are almost certainly these.
- **Trickster** — the query contains **Loki**, so its two giant spikes are the
  Disney+ *Loki* S1 (Jun 2021) and S2 (Oct 2023) premieres. Any near-event
  alignment is coincidence with a release calendar.
- **Fire (inferno + conflagration)** — low-volume and movie-polluted. The huge
  "pre-2016-election" lift (z≈+11) coincides with the Tom Hanks film **Inferno**
  (Oct 2016), not the election. Treat all Fire lifts as suspect.
- **Hero / Warrior / Savior** — the 2008–2009 peak tracks **Guitar Hero**'s peak
  years far more than any event.
- **Blood** — broad, polysemous (medical, gaming e.g. Bloodborne, "blood moon").
  Slow secular rise; the sharp 2025–26 end-spike looks like a recent release,
  not an event.
- **Mother (kali + gaia + witch)** — Kali Linux, Kali Uchis, Gaia.com (streaming,
  ~2016 step-up), *The Witch* (2015). Its rise is largely secular/brand.
- **Serpent / Snake** — flat until ~2017 then rising, with a large spike into
  2025 = **Year of the Snake** (Chinese zodiac, 2025) plus "snake game" revivals.
- **Apocalypse** — its biggest spikes are **calendar prophecies**: Harold Camping
  (May 2011) and the Mayan **2012** date (the Dec-2012 max), not world events.
- **Sun & Moon ratio** — the dramatic 2009–2010 moon surge (ratio dips below 1,
  its only sub-1 stretch) coincides with **Twilight: New Moon** (Nov 2009) /
  *Eclipse* (2010). The long secular decline of the ratio (≈2.2 → ≈1.3) is a
  20-year drift, not event-linked.

## Per-cluster notes (what the curve actually does)

| Cluster | Shape | Mean pre-event lift | Read |
|---|---|---|---|
| Serpent / Snake | flat→rising post-2017, 2025 zodiac spike | +0.25 | secular + zodiac |
| Flood / Deluge | seasonal spikes; big 2011 & 2025 spikes | +0.46 | weather-seasonal; 2011 spike ~ Tohoku/Thailand floods |
| Fire | low-volume, movie spikes | +2.05 | **inflated by tiny baseline + *Inferno* film** |
| Blood | slow rise, 2025 end-spike | +0.38 | polysemous/brand |
| Mother (dark) | secular rise, 2016 step | +0.59 | brand (Gaia/Kali/Witch) |
| Father / King | 2004 spike, decline, recent rise | +0.37 | "king" (Charles III era), Tyrant (2014) |
| Child / Rebirth | flat-low, huge 2024–25 spikes | +0.27 | recent brand spikes; early lifts = tiny baseline |
| Wise Old Man | steady **decline** 2004→2020 | −0.95 | "oracle/sage" software decline; downtrend drives negative |
| Shadow / Double | rises sharply ~2020–21 | +0.18 | gaming/Netflix (*Shadow and Bone* 2021) |
| Trickster | two Loki spikes | −0.07 | **Loki series**, release-calendar |
| Hero / Warrior | 2008–09 peak, then plateau | −0.43 | Guitar Hero era |
| Apocalypse | spikes at 2011 & Dec-2012 | +0.25 | **doomsday-prophecy calendar**, not events |
| Mandala / Wheel | secular rise (coloring-book era) | +1.35 | **inflated by tiny baseline**; secular |
| Dragon | GoT plateau then decay | −0.55 | **GoT/fantasy brand** |
| Tower / Fortress | flat, sharp 2023 spike | −0.19 | "the wall"/tower brand; 2023 spike unexplained |
| Wolf / Beast | 2014 & 2016–17 spikes | +0.34 | **Wolf of Wall St + GoT/BATB** |
| Sun & Moon | ratio secular decline; 2009 Twilight dip | −0.03 | **Twilight** pollution + drift |

## Where an event *does* sit near a symbolic bump (weak, non-systematic)

Even taking the z-scores at face value, the alignments are scattered, not a
pattern, and each has a mundane alternative:

- **Tohoku / Fukushima (Mar 2011)** shows up across several water/upheaval
  clusters at once — Flood (z≈+4.0), Apocalypse (+3.7), Mother (+4.7), Father
  (+3.7). This is the most "poly-symbol" event, but it's also the case most
  exposed to reverse causality: the quake/tsunami/meltdown was a slow-building,
  heavily-covered March story, so "before" and "after" blur at monthly
  resolution.
- **West Africa Ebola (Mar 2014)** coincides with Wolf (+4.9), Shadow (+3.6),
  Tower (+3.3), Mandala (+2.7) — but 2014 is exactly the *Wolf of Wall Street* /
  GoT window, so the Wolf/Shadow bumps are almost certainly brand.
- **Paris attacks (Nov 2015)** sits near Mother (+7.6), Fire (+4.6), Father
  (+3.3) — Mother's number rides the 2015–16 Gaia/Witch step-up.

The recurring lesson: **every apparent pre-event symbolic rise here has a
release-calendar, zodiac, seasonal, or downtrend explanation at least as
plausible as the archetypal one.** Nothing survives that isn't either
brand-driven or a small-baseline artifact. This is the apophenia trap the README
warns about, showing up exactly on schedule.

## Suggested next steps (if pursuing)

1. **Disambiguate queries with topic IDs** (Trends "topic" not "search term") to
   strip the Loki-the-god vs Loki-the-show, dragon-the-symbol vs GoT confound.
2. Run the **null-modeled scan** (`run_scan.py --mode live`) so any lift is
   judged against the term's own empirical null + FDR, not eyeballed.
3. Drop or reformulate the worst-polluted clusters (dragon, wolf, fire,
   trickster, blood, hero) before spending more on them — flagged above.
