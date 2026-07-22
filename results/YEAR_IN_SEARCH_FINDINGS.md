# Bottom-up archetypal read of Google's Year-in-Search 2025

**A different method from the rest of the repo.** Everywhere else we pick symbol
queries and hope they express archetypes (top-down), which drowns in polysemy and
brand noise (dragon = Game of Thrones, trickster = the Loki show). Here we invert
it: take what people *actually* surged toward in 2025 — Google's trending-search
lists — and read the archetypes out of the real terms afterward. This sidesteps
query pollution, at the cost of Google having pre-selected and categorized the
list for us.

**Still a reading, not a measurement.** Each tag is interpretive judgment
(LLM-assisted, human-spot-checkable in `data/year_in_search/2025_classified.csv`).
Two honest people will disagree on some rows. The taxonomy is in
`ontology/archetype_taxonomy.yaml`; re-run `python classify_year_in_search.py`
after editing the CSV to re-summarize.

## Why weekly-over-a-year wasn't possible

The original ask was top trends *per week for the last year*. Google no longer
serves that: the old daily-trends API (`trending_searches` / `today_searches` /
`realtime_trending_searches`) now 404s, and the live "Trending Now" RSS feed is a
right-now snapshot only (~last 24–48h). There is no public weekly archive going
back a year. So we used **Year in Search 2025** — the most recent complete annual
list — as the retrospective proxy. (A true weekly series can only be built
*forward* by snapshotting the live feed on a schedule from here on.)

## The corpus

~90 unique trends across 20 lists (global + US): trending searches, news, AI-image
trends, people, passings, actors, movies, TV, books, games, musicians, songs,
sports. Verbatim in `data/year_in_search/2025.yaml`. Excluded as low archetypal
charge: Maps bookstores/transit, travel itineraries, viral recipes.

Remember these are **trending** (fastest-growing) queries, not highest-volume —
so the list is already tilted toward the year's ruptures and novelties, which is
exactly the archetypal-eruption signal we want, but also means it over-represents
shock events versus steady collective preoccupations.

## What dominated (charge-weighted; primary=1.0, secondary=0.5, ×charge)

| Archetype | Mass | The trends driving it |
|---|---|---|
| **Hero / Warrior** | 26.3 | Superman, KPop Demon Hunters, Zohran Mamdani, Kendrick, the wall of sport (cricket/football/UFC/Ryder), war-combat games |
| **Shadow** | 23.7 | Charlie Kirk assassination + Tyler Robinson, Epstein files, *Monster: Ed Gein*, *Sinners*, *It*, d4vd scandal, Andy Byron |
| **Ruler / Father-King** | 14.4 | Inauguration, One Big Beautiful Bill, shutdown, tariffs, No Kings protest, Pope, *1984*/*Animal Farm*, "Father Figure" |
| **Apocalypse** | 9.4 | LA fires, Hurricane Melissa, Kamchatka quake/tsunami, Iran war, India–Pakistan |
| **Trickster** | 9.1 | DeepSeek, Labubu, the AI-image/meme swarm, Jimmy Kimmel, Bad Bunny |
| **Anima / Eros** | 8.6 | romantasy books, *Hunting Wives*, Bianca Censori, Bonnie Blue, Gatsby |
| **Death** | 7.8 | Charlie Kirk (passing), *Ed Gein*, "The Fate of Ophelia", *Expedition 33* |
| Sage | 5.9 | New Pope / Pope Leo XIV, Gemini, To Kill a Mockingbird |
| persona / serpent-beast / self / rebirth / maiden / divine-child / great-mother | ≤4.4 each | actors & pop image; *Sinners*/dragons/UFC; AI-self-image; Frankenstein/remaster; coming-of-age; prodigies/Ghibli; the mourning/earth feminine |

## Eyeball reading (exploratory, not evidence)

- **2025's collective attention split into a Hero–Shadow dyad.** The two biggest
  masses by far are the striving champion and the dark/destructive — and they're
  often the *same story* (KPop Demon Hunters = hero vs demon; Thunderbolts =
  redeemed villains; the Kirk assassination = a martyr and a murderer at once).
  That polarity, not any single symbol, is the year's shape.
- **The single loudest archetypal event was a sacrificial killing** — the Charlie
  Kirk assassination pulls Shadow *and* Death *and* (for his side) martyr-hero,
  recurring across trending, news, passings, and people. If any 2025 moment reads
  as an archetype erupting into the mass psyche, it's this one.
- **Ruler is unusually loud**, and specifically in its *contested* form:
  coronation (Inauguration, the Pope) sitting right next to revolt ("No Kings",
  shutdown, the dismantling of USAID). The father-king archetype in 2025 shows up
  mostly as a fight *over* the throne.
- **The Trickster wears an AI mask.** DeepSeek the disruptor, the AI-action-figure
  / Barbie / Ghibli / Ghostface image-swarm, and the meme nonsense ("chicken
  jockey", "67") cluster the shapeshifter archetype squarely on generative AI —
  and Gemini (the sage-oracle whose name is literally the Twins) sits on the
  seam between sage and trickster.
- **Apocalypse is entirely literal-elemental** — fire (LA), storm (Melissa),
  flood/quake (Kamchatka), war (Iran, India–Pakistan). No symbolic proxy needed;
  people searched the disasters directly.

## The honest caveats (same discipline as the rest of the repo)

1. **Google pre-shaped the sample.** These are editor-influenced, category-bucketed,
   "fastest-growing" lists — not raw search mass. The category structure itself
   nudges the archetype mix (a big "Sports Events" list guarantees Hero shows up).
2. **The tagging is interpretive and reversible.** Sport-as-Hero and
   celebrity-as-Anima are defensible but soft; down-weight them (they're mostly
   "med"/"low" charge already). The `charge` column exists precisely so you can
   re-run with the soft ones stripped.
3. **This describes 2025's stories, and says nothing about *lead* timing.** The
   whole "does the symbol rise *before* the event" question — the actual
   hypothesis — is untestable from an annual retrospective list. That needs the
   forward weekly archive.

## Suggested next step

Stand up the **forward weekly snapshot** of the live Trending Now RSS (multi-geo,
it carries per-trend start-time and volume). A few months of that gives real
weekly archetype trajectories, and *those* can finally be lined up against event
dates to ask the lead-timing question this project actually cares about.
