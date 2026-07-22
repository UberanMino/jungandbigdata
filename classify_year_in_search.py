#!/usr/bin/env python3
"""Bottom-up archetypal classification of Google Year-in-Search 2025 trends.

Reads the verbatim corpus (data/year_in_search/<year>.yaml), tags every trend
with a primary + secondary Jungian archetype, a "charge" (how strongly it
carries archetypal vs. purely commercial content), and a one-line rationale,
then writes:

  * data/year_in_search/<year>_classified.csv  -- the tagged table (source of
    truth once written; edit it and re-run to re-summarize)
  * results/archetype_distribution_2025.png     -- charge-weighted archetype mix
  * printed summary of which archetypes dominated real collective attention

The tags are an LLM-assisted *reading*, not a measurement -- spot-check the CSV.
"""
from __future__ import annotations

import csv
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
YEAR = 2025
CORPUS = ROOT / "data" / "year_in_search" / f"{YEAR}.yaml"
CLASSIFIED = ROOT / "data" / "year_in_search" / f"{YEAR}_classified.csv"
CHART = ROOT / "results" / f"archetype_distribution_{YEAR}.png"

CHARGE_WEIGHT = {"high": 1.0, "med": 0.6, "low": 0.25, "none": 0.0}

# Archetype display order (matches ontology/archetype_taxonomy.yaml).
ARCHETYPE_ORDER = [
    "hero", "shadow", "trickster", "ruler", "sage", "great_mother", "anima",
    "maiden", "divine_child", "self", "rebirth", "death", "apocalypse",
    "serpent_beast", "persona",
]

# trend name -> (primary, secondary, charge, rationale). Keys cover every string
# in the corpus (including name variants like "LA Fires" / "Los Angeles fires").
TAGS: dict[str, tuple[str, str, str, str]] = {
    # --- AI / tech ---
    "Gemini": ("sage", "trickster", "med", "Google's AI as modern oracle; the name is the Twins (duality/doubling)."),
    "DeepSeek": ("trickster", "sage", "high", "Upstart AI that upended incumbents overnight -- the disruptor/boundary-breaker; also AI-as-oracle."),
    "iPhone 17": ("persona", "", "low", "Consumer fetish object; little mythic depth."),
    # --- the Charlie Kirk cluster (the year's dominant archetypal moment) ---
    "Charlie Kirk": ("death", "shadow", "high", "Slain activist; martyrdom/sacrificial death."),
    "Charlie Kirk assassination": ("shadow", "death", "high", "Political killing -- the violent dark eruption + sacrificial death."),
    "Erika Kirk": ("great_mother", "death", "med", "The public widow; the mourning feminine."),
    "Tyler Robinson": ("shadow", "", "high", "The assassin -- the destroyer figure."),
    # --- war / catastrophe ---
    "Iran": ("apocalypse", "shadow", "high", "2025 strikes/war; fire-and-war end-times imagery + the national 'enemy'."),
    "Pakistan and India": ("apocalypse", "hero", "med", "Cross-border conflict -- war + martial contest."),
    "LA Fires": ("apocalypse", "", "high", "Conflagration -- the destroying/purifying fire."),
    "Los Angeles fires": ("apocalypse", "", "high", "Conflagration."),
    "Hurricane Melissa": ("apocalypse", "great_mother", "high", "Devouring storm -- nature-as-destroyer."),
    "Kamchatka Earthquake and Tsunami": ("apocalypse", "", "high", "Quake + deluge -- the flood that unmakes."),
    # --- state / sovereignty ---
    "One Big Beautiful Bill Act": ("ruler", "", "med", "Sweeping state law -- the sovereign's decree."),
    "Government shutdown": ("ruler", "apocalypse", "med", "Paralysis/collapse of state authority."),
    "US Government Shutdown": ("ruler", "apocalypse", "med", "Paralysis of state authority."),
    "Tariffs": ("ruler", "", "low", "Sovereign economic power; abstract, low mythic charge."),
    "USAID": ("ruler", "great_mother", "low", "State aid apparatus dismantled -- the withdrawn nurturing hand."),
    "No Kings protest": ("ruler", "hero", "high", "Explicit revolt against the father-king."),
    "Epstein files": ("shadow", "", "high", "Hidden corruption dragged to light -- the collective shadow."),
    "US Presidential Inauguration": ("ruler", "", "high", "Coronation of the sovereign."),
    "TikTok ban": ("ruler", "trickster", "med", "The state moving against the platform of memetic chaos -- ruler vs trickster."),
    "New Pope chosen": ("sage", "rebirth", "high", "Election of the spiritual father -- the Wise Old Man renewed."),
    "Pope Leo XIV": ("sage", "ruler", "high", "The spiritual father/sovereign."),
    "Zohran Mamdani": ("hero", "ruler", "high", "Young insurgent becomes sovereign -- new champion + renewal of the city."),
    "Zohran Mamdani elected": ("ruler", "hero", "high", "Accession of a new ruler."),
    # --- sport (ritual combat; brand-diluted) ---
    "India vs England": ("hero", "", "med", "Ritual combat (cricket)."),
    "India vs Australia": ("hero", "", "med", "Ritual combat (cricket)."),
    "Club World Cup": ("hero", "", "med", "Ritual combat (football tournament)."),
    "FIFA Club World Cup": ("hero", "", "med", "Ritual combat (football tournament)."),
    "Asia Cup": ("hero", "", "med", "Ritual combat (cricket)."),
    "ICC Champions Trophy": ("hero", "", "med", "Ritual combat (cricket)."),
    "ICC Women's World Cup": ("hero", "", "med", "Ritual combat (cricket)."),
    "Ryder Cup": ("hero", "", "med", "Ritual combat (golf)."),
    "EuroBasket": ("hero", "", "med", "Ritual combat (basketball)."),
    "Concacaf Gold Cup": ("hero", "", "med", "Ritual combat (football)."),
    "4 Nations Face-Off": ("hero", "", "med", "Ritual combat (hockey)."),
    "UFC 313": ("hero", "serpent_beast", "med", "Single combat -- the warrior/beast."),
    "UFC 311": ("hero", "serpent_beast", "med", "Single combat -- the warrior/beast."),
    # --- viral toy / AI-image / meme trends ---
    "Labubu": ("trickster", "serpent_beast", "med", "Beloved little-monster toy craze -- the domesticated imp / cute-shadow."),
    "AI action figure": ("self", "persona", "med", "Turning oneself into a doll/idol -- self-image made object."),
    "AI Barbie": ("self", "persona", "med", "Self-as-doll; idealized image."),
    "AI Ghostface": ("shadow", "trickster", "med", "Horror-mask self-image -- playing with the shadow."),
    "AI Polaroid": ("self", "persona", "low", "Nostalgic self-image."),
    "Ghibli": ("divine_child", "self", "med", "AI-Ghibli images -- the childlike numinous world; wonder."),
    "Holy airball": ("trickster", "", "low", "Sports-meme absurdity."),
    "Chicken jockey": ("trickster", "", "low", "Minecraft-movie meme; absurd inversion."),
    "Bacon avocado": ("trickster", "", "low", "Food meme; nonsense."),
    "Anxiety dance": ("trickster", "shadow", "low", "Mocking dread through absurd performance."),
    "Unfortunately I do love": ("trickster", "", "low", "Ironic catchphrase meme."),
    # --- people ---
    "d4vd": ("shadow", "anima", "high", "Young heartthrob engulfed by a dark death-scandal -- persona swallowed by shadow."),
    "Kendrick Lamar": ("hero", "", "med", "The bard-champion (Super Bowl) -- cultural warrior."),
    "Jimmy Kimmel": ("trickster", "ruler", "med", "The jester suspended/reinstated over Kirk remarks -- jester vs authority."),
    "Vaibhav Sooryavanshi": ("divine_child", "hero", "med", "Teen cricket prodigy -- the wonder-child."),
    "Shedeur Sanders": ("hero", "shadow", "med", "The anointed young QB whose draft 'fall' became the story."),
    "Bianca Censori": ("anima", "persona", "med", "The eroticized spectacle/muse."),
    "Greta Thunberg": ("hero", "great_mother", "med", "The crusader / earth-defender."),
    "Bonnie Blue": ("anima", "shadow", "med", "Shadow-eros; the transgressive/devouring feminine spectacle."),
    "Karoline Leavitt": ("ruler", "persona", "low", "The sovereign's herald (press secretary)."),
    "Andy Byron": ("shadow", "trickster", "med", "The 'kiss-cam' CEO -- the exposed secret + public humiliation."),
    # --- actors (mostly persona) ---
    "Mikey Madison": ("persona", "anima", "low", "Star image (Anora)."),
    "Lewis Pullman": ("persona", "", "low", "Star image."),
    "Isabela Merced": ("persona", "", "low", "Star image."),
    "Song Ji Woo": ("persona", "", "low", "Star image."),
    "Kaitlyn Dever": ("persona", "", "low", "Star image."),
    "Pedro Pascal": ("persona", "ruler", "low", "Star image (often the protector-father)."),
    "Malachi Barton": ("persona", "maiden", "low", "Young star image."),
    "Walton Goggins": ("persona", "shadow", "low", "Star image (often plays heels)."),
    "Pamela Anderson": ("anima", "persona", "low", "The eroticized icon in a late-career 'unmasked' turn."),
    "Charlie Sheen": ("shadow", "persona", "low", "The fallen-star image; public shadow."),
    # --- movies ---
    "Anora": ("maiden", "anima", "med", "Sex-worker Cinderella -- the maiden's precarious threshold."),
    "Superman": ("hero", "", "high", "The archetypal savior-hero."),
    "Minecraft Movie": ("divine_child", "self", "med", "World-building play -- creation/wholeness."),
    "The Minecraft Movie": ("divine_child", "self", "med", "World-building play -- creation/wholeness."),
    "Thunderbolts": ("shadow", "hero", "med", "A team of redeemed villains -- integrating the shadow."),
    "Sinners": ("serpent_beast", "shadow", "high", "Vampire horror -- the beast/blood + the dark."),
    "KPop Demon Hunters": ("hero", "shadow", "high", "Literal hero-vs-demon myth -- the monster-slaying quest."),
    "Happy Gilmore 2": ("trickster", "", "low", "Comedy -- the fool."),
    # --- TV ---
    "Monster: The Ed Gein Story": ("shadow", "death", "high", "The literal monster/killer -- the devouring dark."),
    "The Hunting Wives": ("anima", "shadow", "med", "Eros + murder -- the femme-fatale shadow."),
    # --- books ---
    "Regretting You": ("anima", "maiden", "low", "Romance/family melodrama."),
    "Onyx Storm": ("serpent_beast", "anima", "med", "Dragon 'romantasy' -- the dragon + eros."),
    "Lights Out": ("anima", "shadow", "med", "Dark romance -- eros in the shadow."),
    "The Summer I Turned Pretty": ("maiden", "anima", "med", "Coming-of-age first love."),
    "The Housemaid": ("shadow", "", "med", "Domestic thriller -- the hidden menace."),
    "Frankenstein": ("rebirth", "shadow", "high", "Reanimation + the created monster -- death/rebirth and the shadow-double."),
    "It": ("shadow", "trickster", "high", "The fear-eating clown -- trickster-shadow devouring children."),
    "Animal Farm": ("ruler", "shadow", "high", "Corruption of power -- the ruler turned devourer."),
    "1984": ("ruler", "shadow", "high", "The total surveillance state -- the devouring father-king."),
    "The Witcher": ("hero", "serpent_beast", "med", "The monster-slayer's quest."),
    "Diary of a Wimpy Kid": ("maiden", "trickster", "low", "Childhood/school foibles -- the young fool."),
    "The Great Gatsby": ("anima", "hero", "med", "Longing for the idealized beloved -- the doomed romantic quest."),
    "To Kill a Mockingbird": ("hero", "sage", "med", "Moral courage; the just father (Atticus) as sage."),
    # --- games ---
    "Arc Raiders": ("hero", "", "med", "Cooperative combat/survival -- the warrior."),
    "ARC Raiders": ("hero", "", "med", "Cooperative combat/survival -- the warrior."),
    "Battlefield 6": ("hero", "apocalypse", "med", "War combat."),
    "Strands": ("self", "", "low", "Word-weaving puzzle -- pattern/wholeness (weak)."),
    "Split Fiction": ("self", "hero", "med", "Two-worlds duality co-op -- doubling/integration."),
    "Clair Obscur: Expedition 33": ("death", "hero", "high", "A doomed annual expedition against mortality -- the death/rebirth quest."),
    "Hollow Knight: Silksong": ("hero", "shadow", "med", "The small knight's descent into the abyss."),
    "The Elder Scrolls IV: Oblivion Remastered": ("rebirth", "apocalypse", "med", "A literal remaster (rebirth) of a game about the gates of 'Oblivion'."),
    # --- musicians ---
    "KATSEYE": ("persona", "anima", "low", "Pop-group image."),
    "Bad Bunny": ("trickster", "hero", "med", "Genre-bending shapeshifter; cultural champion."),
    "Sombr": ("persona", "anima", "low", "Young-artist image."),
    "Doechii": ("trickster", "anima", "med", "Boundary-breaking performer."),
    # --- songs ---
    "Wood": ("trickster", "anima", "low", "Innuendo pop (Taylor Swift) -- ribald play."),
    "DtMF": ("rebirth", "", "low", "Bad Bunny's 'debi tirar mas fotos' -- longing for the past."),
    "Golden (HUNTR/X)": ("hero", "", "med", "Anthem from the demon-hunter film -- the golden hero."),
    "The Fate of Ophelia": ("death", "anima", "high", "Ophelia = the drowning maiden -- death + anima."),
    "Father Figure": ("ruler", "", "med", "Explicit father archetype (Taylor Swift)."),
}


def build_rows() -> list[dict]:
    corpus = yaml.safe_load(CORPUS.read_text())
    rows, unmatched = [], set()
    for list_name, spec in corpus["lists"].items():
        scope = spec.get("scope", "")
        for rank, trend in enumerate(spec["items"], start=1):
            tag = TAGS.get(trend)
            if tag is None:
                unmatched.add(trend)
                tag = ("persona", "", "low", "UNCLASSIFIED -- add to TAGS")
            primary, secondary, charge, rationale = tag
            rows.append({
                "scope": scope, "list": list_name, "rank": rank, "trend": trend,
                "archetype_primary": primary, "archetype_secondary": secondary,
                "charge": charge, "rationale": rationale,
            })
    if unmatched:
        print("WARNING unclassified trends:", sorted(unmatched))
    return rows


def write_csv(rows: list[dict]) -> None:
    CLASSIFIED.parent.mkdir(parents=True, exist_ok=True)
    cols = ["scope", "list", "rank", "trend", "archetype_primary",
            "archetype_secondary", "charge", "rationale"]
    with CLASSIFIED.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def load_rows() -> list[dict]:
    with CLASSIFIED.open() as f:
        return list(csv.DictReader(f))


def distribution(rows: list[dict]) -> dict[str, float]:
    """Charge-weighted archetype mass: primary counts full, secondary half."""
    mass = {a: 0.0 for a in ARCHETYPE_ORDER}
    for r in rows:
        w = CHARGE_WEIGHT.get(r["charge"], 0.0)
        if r["archetype_primary"] in mass:
            mass[r["archetype_primary"]] += w
        if r["archetype_secondary"] in mass:
            mass[r["archetype_secondary"]] += 0.5 * w
    return mass


def plot(mass: dict[str, float]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    items = sorted(mass.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(labels[::-1], vals[::-1], color="#4C6EF5")
    ax.set_xlabel("charge-weighted archetype mass (primary=1, secondary=0.5)")
    ax.set_title(f"Archetypal mix of Google's top trending searches, {YEAR}")
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.1, i, f"{v:.1f}", va="center", fontsize=8)
    fig.tight_layout()
    CHART.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHART, dpi=130)
    plt.close(fig)


def main() -> None:
    if not CLASSIFIED.exists():
        rows = build_rows()
        write_csv(rows)
        print(f"Wrote {CLASSIFIED} ({len(rows)} rows)")
    else:
        rows = load_rows()
        print(f"Loaded existing {CLASSIFIED} ({len(rows)} rows) -- delete it to regenerate from TAGS")

    mass = distribution(rows)
    plot(rows and mass)
    print(f"Wrote {CHART}\n")
    print("Archetype mix (charge-weighted), top to bottom:")
    for a, v in sorted(mass.items(), key=lambda kv: kv[1], reverse=True):
        if v > 0:
            print(f"  {a:14s} {v:5.1f}")


if __name__ == "__main__":
    main()
