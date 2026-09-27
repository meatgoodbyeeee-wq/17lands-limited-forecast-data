#!/usr/bin/env python3
"""Two candidate feature families for the 21-set GIH research (pre-release information only).

C1  ability condition / efficiency  (card text only)
    Distinguishes self-sufficient, high-impact effects (mass removal, several bodies,
    multi-mode spells, recurring value) from effects gated on the player's own actions,
    conditions and drawbacks. Chosen from the baseline OOF residual audit: the largest
    over-predictions are build-around / gated engines, the largest under-predictions are
    wraths, multi-body token makers, commands and recurring value.

C2  ability x environment fit  (card text + that set's full booster card pool)
    For cards whose value depends on a card class (spells, artifacts, tokens, graveyard,
    a creature type, ...), the share of the set's commons/uncommons in the card's colours
    that supply that class. The pool comes from Scryfall booster-legal cards, i.e. the
    spoiler, never from 17Lands play counts. Differs from the reverted 0d075bc experiment,
    which used set-level constants (densities) rather than per-card dependency support.
"""
import json, re, time, urllib.error, urllib.parse, urllib.request, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="This pattern is interpreted as a regular expression")

# ---------------------------------------------------------------- C1
NUM = r"(?:two|three|four|five|six|x|that many|a number of|\d+)"
C1_PATTERNS = {
    "c1_mass_removal": r"(destroy|exile) all (other )?(creatures|nonland permanents|permanents|artifacts|nonland|attacking)"
                       r"|all (other )?creatures get -|each (other )?creature gets -|damage to each (other )?creature"
                       r"|each creature (your opponents control|an opponent controls) gets -",
    "c1_multi_body": rf"create {NUM} [^.]*creature tokens?|create [^.]*creature token[^.]* and [^.]*creature token",
    "c1_modal_multi": r"choose two|choose one or more|choose any number|choose up to (two|three|four|five)|choose three",
    "c1_recurring_value": r"at the beginning of (your|each) (upkeep|end step|precombat main|combat)[^.]*"
                          r"(draw|create|put a \+1/\+1 counter|deals? \d+ damage|loses? \d+ life|return)",
    "c1_drawback_entry": r"enters tapped|stun counters?|doesn't untap|can't block|skip your|you lose \d+ life"
                         r"|sacrifice (it|this|~)[^.]* at the beginning|at the beginning of your upkeep, sacrifice",
    "c1_symmetric": r"each player (draws|sacrifices|discards|mills|exiles|loses|may)",
    "c1_gated_trigger": r"whenever you (cast|scry|surveil|sacrifice|discard|gain life|draw your second|attack with (two|three)"
                        r"|create|mill|expend|cycle|commit)|if an effect would|whenever one or more (other )?"
                        r"(artifacts?|enchantments?|tokens?|cards?) (you control )?(enter|leave|are put)",
}
COND_WORDS = [r"\bif you control\b", r"\bas long as\b", r"\bactivate only\b", r"\bonly if\b", r"\bunless\b",
              r"\bif you've\b", r"\bif it's your\b", r"\bthreshold\b", r"\bdelirium\b", r"\bdescend\b",
              r"\bif you have\b", r"\bif there are\b", r"\bif a creature died this turn\b"]


def _tokens_power(tl):
    ps = [int(m.group(1)) for m in re.finditer(r"create[^.]*?(\d+)/(\d+)[^.]*creature token", tl)]
    return max(ps) if ps else 0


def add_c1(d):
    tl = d["oracle_text"].fillna("").str.lower()
    out = pd.DataFrame(index=d.index)
    for k, pat in C1_PATTERNS.items():
        out[k] = tl.str.contains(pat, regex=True).astype(int)
    out["c1_condition_count"] = sum(tl.str.count(p) for p in COND_WORDS)
    out["c1_token_power"] = tl.map(_tokens_power)
    out["c1_impact_score"] = (out["c1_mass_removal"]*2 + out["c1_multi_body"] + out["c1_modal_multi"]
                              + out["c1_recurring_value"] + (out["c1_token_power"] >= 3).astype(int))
    out["c1_friction_score"] = (out["c1_drawback_entry"] + out["c1_symmetric"] + out["c1_gated_trigger"]
                                + out["c1_condition_count"].clip(upper=3))
    out["c1_net_self_sufficiency"] = out["c1_impact_score"] - out["c1_friction_score"]
    mv = d["mv"].clip(lower=1)
    out["c1_impact_per_mv"] = out["c1_impact_score"] / mv
    return out


# ---------------------------------------------------------------- C2
# dependency pattern on the card itself  ->  enabler pattern on other pool cards
DEPS = {
    "spells": (r"whenever you cast an? (instant|sorcery|noncreature)|instant (and|or) sorcery (spells|cards)"
               r"|instants? and sorcer(y|ies) you|magecraft|prowess|for each instant",
               lambda p: p["is_instant_sorcery"]),
    "artifacts": (r"artifacts? you control|whenever [^.]*artifact[^.]* enters|for each artifact|affinity for artifacts"
                  r"|improvise|artifact spells? you cast",
                  lambda p: p["is_artifact"] | p["txt"].str.contains(r"create[^.]*(treasure|clue|food|blood|map|powerstone|gold|junk|artifact)[^.]*token", regex=True)),
    "enchantments": (r"enchantments? you control|whenever [^.]*enchantment[^.]* enters|constellation|for each enchantment"
                     r"|eerie", lambda p: p["is_enchantment"]),
    "tokens": (r"tokens? you control|whenever [^.]*token[^.]* enters|if an effect would create|for each token"
               r"|create a token that's a copy", lambda p: p["txt"].str.contains(r"create[^.]* token", regex=True)),
    "sacrifice_death": (r"whenever (you sacrifice|another creature you control dies|a creature you control dies|one or more"
                        r" other creatures you control die)|sacrifice another|whenever another creature dies",
                        lambda p: p["txt"].str.contains(r"create[^.]*creature token|sacrifice (a|another) (creature|artifact|permanent)", regex=True)),
    "graveyard": (r"cards? in your graveyard|from your graveyard|delirium|threshold|descend|for each [^.]* in your graveyard",
                  lambda p: p["txt"].str.contains(r"\bmill|surveil|discard|put [^.]* into your graveyard|self-mill", regex=True)),
    "counters": (r"with (a |one or more )?\+1/\+1 counters? on (it|them)|whenever [^.]*(counters? (is|are) put|put one or more)"
                 r"|for each \+1/\+1 counter", lambda p: p["txt"].str.contains(r"\+1/\+1 counter", regex=True)),
    "lifegain": (r"whenever you gain life|if you gained life", lambda p: p["txt"].str.contains(r"gain \d+ life|lifelink|gain life", regex=True)),
    "scry_surveil": (r"whenever you (scry|surveil)", lambda p: p["txt"].str.contains(r"scry|surveil", regex=True)),
    "legendary_historic": (r"historic|legendary (creatures?|spells?|permanents?) you (control|cast)|whenever you cast a legendary",
                           lambda p: p["is_legendary"] | p["is_artifact"] | p["type_line"].str.contains("Saga")),
    "multicolor": (r"multicolored (spells?|permanents?|creatures?) you|whenever you cast a multicolored",
                   lambda p: p["n_colors"] >= 2),
}
IRREGULAR = {"Elf": "Elves", "Dwarf": "Dwarves", "Wolf": "Wolves", "Werewolf": "Werewolves", "Fox": "Foxes"}


def set_subtypes(pool):
    """Creature subtypes printed on the set's own creature/kindred cards (spoiler information)."""
    st = set()
    for t in pool["type_line"]:
        for face in t.split("//"):
            if ("Creature" in face or "Kindred" in face or "Tribal" in face) and "—" in face:
                st.update(w for w in face.split("—", 1)[1].split() if w[:1].isupper())
    return st


def tribal_types(raw, subtypes):
    """Subtypes the card rewards: '<Type>s you control', 'other <Type>s', '<Type> spells you cast'."""
    hits = set()
    for t in subtypes:
        forms = [t, t + "s", IRREGULAR.get(t, t + "s")]
        alt = "|".join(re.escape(f) for f in forms)
        if re.search(rf"\b(?:{alt})\b(?:[^.]{{0,25}})(?:you control|you cast|creatures? you control)"
                     rf"|\b(?:other|another|each) (?:{alt})\b", raw):
            hits.add(t)
    return hits


def _colors_overlap(a, b):
    return (not a) or (not b) or bool(set(a) & set(b))


def add_c2(d, pools):
    """pools: DataFrame with set, name, rarity, colors(list), type_line, txt (lowercase oracle)."""
    tl = d["oracle_text"].fillna("").str.lower()
    raw = d["oracle_text"].fillna("")
    out = pd.DataFrame(index=d.index, columns=["c2_dep_count","c2_support_mean","c2_support_min","c2_tribal_support",
                                               "c2_dep_x_lowsupport"], dtype=float)
    pools = pools.copy()
    pools["is_instant_sorcery"] = pools["type_line"].str.contains("Instant|Sorcery")
    pools["is_artifact"] = pools["type_line"].str.contains("Artifact")
    pools["is_enchantment"] = pools["type_line"].str.contains("Enchantment")
    pools["is_legendary"] = pools["type_line"].str.contains("Legendary")
    pools["n_colors"] = pools["colors"].map(len)
    cu = pools[pools["rarity"].isin(["common","uncommon"])]
    by_set = {s: g.reset_index(drop=True) for s, g in cu.groupby("set")}
    subtypes = {s: set_subtypes(g) for s, g in pools.groupby("set")}
    enabler_cache = {}
    for s, g in by_set.items():
        enabler_cache[s] = {k: fn(g).astype(bool).to_numpy() for k, (_, fn) in DEPS.items()}
    card_colors = d["__colors"]
    for i in d.index:
        s = d.at[i, "set"]; g = by_set.get(s)
        if g is None:
            raise SystemExit(f"No pool for {s}")
        mask_col = np.array([_colors_overlap(card_colors[i], c) for c in g["colors"]]) & (g["name"] != d.at[i, "name"]).to_numpy()
        denom = max(int(mask_col.sum()), 1)
        sup = []
        for k, (pat, _) in DEPS.items():
            if re.search(pat, tl[i]):
                sup.append(float((enabler_cache[s][k] & mask_col).sum()) / denom)
        types = tribal_types(raw[i], subtypes[s])
        trib = np.nan
        if types:
            has = g["type_line"].map(lambda t: any(re.search(rf"\b{re.escape(x)}\b", t) for x in types)).to_numpy()
            trib = float((has & mask_col).sum()) / denom
            sup.append(trib)
        out.at[i, "c2_dep_count"] = len(sup)
        out.at[i, "c2_support_mean"] = float(np.mean(sup)) if sup else 1.0
        out.at[i, "c2_support_min"] = float(np.min(sup)) if sup else 1.0
        out.at[i, "c2_tribal_support"] = trib if types else 1.0
        out.at[i, "c2_dep_x_lowsupport"] = len(sup) * (1.0 - (float(np.min(sup)) if sup else 1.0))
    return out.astype(float)


# ---------------------------------------------------------------- Scryfall pools
def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "LimitedForecastResearch/2.0", "Accept": "application/json"})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 7:
                raise
            time.sleep(min(2**attempt, 30))


def fetch_pool(code):
    url = "https://api.scryfall.com/cards/search?q=" + urllib.parse.quote(f"e:{code.lower()}")
    rows = []
    while url:
        js = _get_json(url)
        for c in js["data"]:
            if not c.get("booster"):
                continue
            faces = c.get("card_faces") or []
            typ = c.get("type_line") or " // ".join(f.get("type_line", "") for f in faces)
            if "Basic Land" in typ or "Token" in typ:
                continue
            text = c.get("oracle_text") or "\n".join(f.get("oracle_text", "") for f in faces)
            colors = c.get("colors") or sorted({z for f in faces for z in f.get("colors", [])})
            rows.append({"set": code.upper(), "name": c["name"], "rarity": c.get("rarity"), "colors": "".join(colors),
                         "type_line": typ, "oracle_text": text})
        url = js.get("next_page") if js.get("has_more") else None
        time.sleep(0.1)
    return pd.DataFrame(rows).drop_duplicates("name")


def prepare_pools(df):
    p = df.copy()
    p["colors"] = p["colors"].fillna("").map(list)
    p["txt"] = p["oracle_text"].fillna("").str.lower()
    p["type_line"] = p["type_line"].fillna("")
    return p
