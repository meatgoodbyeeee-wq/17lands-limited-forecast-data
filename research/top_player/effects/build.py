"""Per-card top-specific difference joined with effect/ability tags (exploratory).
Top (T) = win-rate bucket >= 0.60 and n >= 50. Compared with A = everyone else (the rest of "all users") and with
N = normal players (bucket 0.48-0.60, n >= 50). For each metric m in GIH / GNS / IWD (pp):
  e = T_c - b * X_c   (centred within the set, slope b fitted per set)
  e0 = T(half 0)_c - b * X(half 1)_c,  e1 = T(half 1)_c - b * X(half 0)_c   (independent games)
Tags: C5 atomic effects, C4 finer effects (both judged from text only, names hidden), plus regex features from the text.
Usage: python3 build.py <out.csv.gz>"""
import sys, glob, re
from pathlib import Path
import numpy as np, pandas as pd
D = Path("research/top_player/skill_compare/data")
sets = sorted(Path(f).name.split("_")[0] for f in glob.glob(str(D / "*_cards.csv.gz")))
C = pd.concat([pd.read_csv(D / f"{s}_cards.csv.gz", dtype={"half": str, "period": str}) for s in sets], ignore_index=True)
M = ["pool_g", "deck_g", "deck_w", "gih_g", "gih_w", "gns_g", "gns_w", "oh_g", "oh_w", "gd_g", "gd_w"]
GR = {"T": ["B4", "B5"], "A": ["L", "B1", "B2", "B3"], "N": ["B2", "B3"]}
INFL = 0.958
def agg(g, half=None):
    x = C[C.grp.isin(GR[g])]
    if half is not None: x = x[x.half == half]
    x = x.groupby(["set", "card_name"])[M].sum()
    with np.errstate(divide="ignore", invalid="ignore"):
        x["gih"] = 100 * x.gih_w / x.gih_g; x["gns"] = 100 * x.gns_w / x.gns_g; x["iwd"] = x.gih - x.gns
        x["oh"] = 100 * x.oh_w / x.oh_g; x["gd"] = 100 * x.gd_w / x.gd_g; x["rate"] = x.deck_g / x.pool_g
    return x.replace([np.inf, -np.inf], np.nan)
F = {g: agg(g) for g in GR}; H = {(g, h): agg(g, h) for g in GR for h in ("0", "1")}
out = []
for s in sets:
    base = pd.DataFrame({"T_gih_g": F["T"].loc[s].gih_g, "A_gih_g": F["A"].loc[s].gih_g, "N_gih_g": F["N"].loc[s].gih_g,
                         "T_gns_g": F["T"].loc[s].gns_g, "T_gih": F["T"].loc[s].gih, "A_gih": F["A"].loc[s].gih, "N_gih": F["N"].loc[s].gih,
                         "rate_T": F["T"].loc[s].rate, "rate_A": F["A"].loc[s].rate, "rate_N": F["N"].loc[s].rate})
    base = base[(base.T_gih_g >= 500) & (base.A_gih_g >= 500)]
    for X in ("A", "N"):
        for m in ("gih", "gns", "iwd", "oh", "gd"):
            cols = {"T": F["T"].loc[s][m], "X": F[X].loc[s][m], "T0": H[("T", "0")].loc[s][m], "T1": H[("T", "1")].loc[s][m], "X0": H[(X, "0")].loc[s][m], "X1": H[(X, "1")].loc[s][m]}
            x = pd.DataFrame(cols).reindex(base.index)
            ok = x.notna().all(1)
            if m in ("gns", "iwd"): ok &= (F["T"].loc[s].gns_g.reindex(base.index) >= 300)
            if m == "oh": ok &= (F["T"].loc[s].oh_g.reindex(base.index) >= 300)
            if m == "gd": ok &= (F["T"].loc[s].gd_g.reindex(base.index) >= 300)
            y = x[ok]; c = y - y.mean()
            b = np.polyfit(c.X, c["T"], 1)[0]
            base.loc[y.index, f"e_{m}_{X}"] = c["T"] - b * c.X
            base.loc[y.index, f"e0_{m}_{X}"] = c.T0 - b * c.X1
            base.loc[y.index, f"e1_{m}_{X}"] = c.T1 - b * c.X0
            if m == "gih":
                base[f"b_{X}"] = b; base[f"{X}_c"] = c.X; base[f"{X}0_c"] = c.X0
                pT, pX = F["T"].loc[s].gih.reindex(base.index) / 100, F[X].loc[s].gih.reindex(base.index) / 100
                base[f"v_{X}"] = INFL * 1e4 * (pT * (1 - pT) / base.T_gih_g + b * b * pX * (1 - pX) / base[f"{X}_gih_g"])
    base["rate_diff_A"] = base.rate_T - base.rate_A
    base.insert(0, "set", s); out.append(base.reset_index())
E = pd.concat(out, ignore_index=True)
order = pd.Series({s: pd.read_json(D / f"{s}_skill_manifest.json", typ="series").window_start for s in sets}).sort_values()
E["set_order"] = E.set.map({s: i for i, s in enumerate(order.index)})

# ---- tags
front = lambda k: k.str.split(" // ").str[0]
def load(f, keycol="key"):
    x = pd.read_csv(f); x["set"] = x[keycol].str.split("|").str[0]; x["card_name"] = front(x[keycol].str.split("|", n=1).str[1])
    return x.drop_duplicates(["set", "card_name"]).drop(columns=[keycol, "id"], errors="ignore")
c5 = load("research/c5_atomic_effects/c5_features.csv.gz"); c4 = load("research/c4_fine_effects/c4_features.csv.gz")
tx = load("research/c14_context_power/set_cards.csv.gz")[["set", "card_name", "type", "text", "mv", "colors", "pt", "rar"]]
E = E.merge(tx, on=["set", "card_name"], how="left").merge(c5, on=["set", "card_name"], how="left").merge(c4, on=["set", "card_name"], how="left")
E["tagged"] = E.c5_RATE.notna() & E.type.notna()
t = E.type.fillna(""); txt = E.text.fillna("")
E["is_land"] = t.str.contains("Land") & ~t.str.contains("Creature")
E["is_creature"] = t.str.contains("Creature"); E["is_instant"] = t.str.contains("Instant"); E["is_sorcery"] = t.str.contains("Sorcery")
E["is_artifact"] = t.str.contains("Artifact") & ~E.is_creature; E["is_enchantment"] = t.str.contains("Enchantment") & ~E.is_creature
E["is_aura"] = t.str.contains("Aura"); E["is_equipment"] = t.str.contains("Equipment"); E["is_vehicle"] = t.str.contains("Vehicle")
E["is_saga"] = t.str.contains("Saga"); E["is_legendary"] = t.str.contains("Legendary"); E["is_pw"] = t.str.contains("Planeswalker")
col = E.colors.fillna("").astype(str).replace("nan", "")
for k in "WUBRG": E["col_" + k] = col.str.contains(k)
E["ncol"] = col.str.len(); E["col_multi"] = E.ncol >= 2; E["col_none"] = (E.ncol == 0)
pt = E.pt.fillna("").astype(str).str.extract(r"^(\d+)/(\d+)$")
E["power"] = pd.to_numeric(pt[0], errors="coerce"); E["tough"] = pd.to_numeric(pt[1], errors="coerce")
rx = lambda p: txt.str.contains(p, case=False, regex=True)
E["x_words"] = txt.str.split().str.len().fillna(0)
E["x_activated"] = txt.str.contains(r"(?:^|\n|\")[^\n\"]*(?:\{[^}]+\}|\bTap\b|Sacrifice|Discard|Pay)[^\n\".]*:", regex=True)
E["x_tap_ability"] = txt.str.contains(r"\{T\}[^\n:]*:", regex=True)
E["x_mana_ability"] = txt.str.contains(r"\{T\}[^\n:]*: Add", regex=True)
E["x_instant_speed_act"] = E.x_activated & ~txt.str.contains("Activate only as a sorcery", case=False)
E["x_target"] = rx(r"\btarget\b"); E["x_ntarget"] = txt.str.count(r"(?i)\btarget\b")
E["x_choice"] = rx(r"\bchoose (?:one|two|up to|any)|\byou may\b|\bor\b")
E["x_you_may"] = rx(r"\byou may\b")
E["x_xcost"] = rx(r"\{X\}"); E["x_graveyard"] = rx(r"graveyard"); E["x_library_top"] = rx(r"top (?:\w+ )?cards? of your library|scry|surveil|look at the top")
E["x_surveil_scry"] = rx(r"\bscry\b|\bsurveil\b"); E["x_loot"] = rx(r"draw (?:a|two|\w+) cards?,? then discard|discard a card, then draw|discard a card\. If you do, draw")
E["x_sac_cost"] = rx(r"sacrifice (?:a|an|another|this|~)[^.\n]*:"); E["x_sacrifice"] = rx(r"\bsacrifice\b")
E["x_discard_self"] = rx(r"discard (?:a|two|your)"); E["x_opp_discard"] = rx(r"(?:target (?:player|opponent)|each opponent)[^.]*discards?")
E["x_counter_spell"] = rx(r"counter target"); E["x_prowess_like"] = rx(r"whenever you cast (?:a|an|your)[^.]*(?:noncreature|instant|sorcery)")
E["x_defender"] = rx(r"\bdefender\b"); E["x_cant_block"] = rx(r"can't block"); E["x_unblockable"] = rx(r"can't be blocked")
E["x_end_step"] = rx(r"end step"); E["x_upkeep"] = rx(r"upkeep"); E["x_combat_damage_trigger"] = rx(r"deals combat damage to a player")
E["x_attacks_trigger"] = rx(r"whenever (?:~|this creature|a creature you control|one or more creatures you control) attacks?")
E["x_etb"] = rx(r"when (?:~|this \w+) enters|enters the battlefield"); E["x_dies"] = rx(r"\bdies\b")
E["x_lifegain"] = rx(r"you gain \w+ life|lifelink"); E["x_lifegain_payoff"] = rx(r"whenever you gain life")
E["x_draw"] = rx(r"draws? (?:a|an additional|two|three|x|that many) cards?"); E["x_draw2"] = rx(r"draws? (?:two|three|four|x|that many) cards")
E["x_mill"] = rx(r"\bmills?\b"); E["x_exile_gy"] = rx(r"exile[^.]*from (?:a|your|target player's) graveyard")
E["x_return_hand_own"] = rx(r"return (?:target|a|up to \w+)[^.]*from your graveyard to your hand"); E["x_reanimate"] = rx(r"from (?:your|a) graveyard to the battlefield")
E["x_token"] = rx(r"create[^.]*token"); E["x_treasure"] = rx(r"treasure"); E["x_food"] = rx(r"\bfood\b"); E["x_clue"] = rx(r"\bclue\b|investigate")
E["x_counters_p1"] = rx(r"\+1/\+1 counter"); E["x_counters_m1"] = rx(r"-1/-1 counter"); E["x_proliferate"] = rx(r"proliferate")
E["x_pump_until_eot"] = rx(r"gets? \+\d+/\+\d+[^.]*until end of turn"); E["x_team_pump"] = rx(r"creatures you control get \+")
E["x_hexproof_ind"] = rx(r"hexproof|indestructible|protection from"); E["x_ward"] = rx(r"\bward\b")
E["x_bounce"] = rx(r"return target[^.]*to (?:its|their) owner's hand"); E["x_tap_down"] = rx(r"tap target|doesn't untap|stun counter")
E["x_fight_bite"] = rx(r"\bfights?\b|deals damage equal to its power to"); E["x_destroy"] = rx(r"destroy target"); E["x_exile_target"] = rx(r"exile target")
E["x_damage_any"] = rx(r"deals? \w+ damage to any target"); E["x_damage_creature"] = rx(r"deals? \w+ damage to target (?:creature|attacking|blocking)")
E["x_minus"] = rx(r"gets? -\d+/-\d+"); E["x_edict"] = rx(r"(?:target|each) (?:opponent|player) sacrifices")
E["x_flash"] = rx(r"(?:^|\n)flash\b|\bflash\b"); E["x_flying"] = rx(r"\bflying\b"); E["x_haste"] = rx(r"\bhaste\b"); E["x_trample"] = rx(r"\btrample\b")
E["x_menace"] = rx(r"\bmenace\b"); E["x_deathtouch"] = rx(r"\bdeathtouch\b"); E["x_lifelink"] = rx(r"\blifelink\b"); E["x_vigilance"] = rx(r"\bvigilance\b")
E["x_reach"] = rx(r"\breach\b"); E["x_first_strike"] = rx(r"first strike|double strike")
E["x_cycling"] = rx(r"cycling"); E["x_kicker"] = rx(r"\bkicker\b|\bkicked\b"); E["x_flashback"] = rx(r"flashback|escape|disturb|harmonize"); E["x_modal"] = rx(r"choose (?:one|two)")
E["x_cost_reduce"] = rx(r"costs? \{?\d?\}? ?less to cast"); E["x_alt_cast"] = rx(r"without paying its mana cost|rather than pay")
E["x_instant_sorcery_matters"] = rx(r"instant (?:or|and) sorcery|instants and sorceries|noncreature spell")
E["x_artifact_matters"] = rx(r"artifacts? you control|whenever (?:an|another) artifact|for each artifact"); E["x_ench_matters"] = rx(r"enchantments? you control|whenever (?:an|another) enchantment|constellation")
E["x_tribal"] = txt.str.contains(r"(?:other|each|another|for each|number of) [A-Z][a-z]+s? you control|[A-Z][a-z]+s you control (?:get|have)", regex=True)
E["x_vanilla"] = E.is_creature & (E.x_words == 0); E["x_french_vanilla"] = E.is_creature & (E.x_words > 0) & (E.x_words <= 3)
E["x_landcycle_fix"] = rx(r"search your library for a (?:basic )?(?:land|plains|island|swamp|mountain|forest)|add one mana of any color|landcycling")
E["x_opp_turn"] = rx(r"during (?:each|an) opponent's turn|on each opponent's turn|whenever an opponent")
E["x_your_turn_only"] = rx(r"during your turn|activate only as a sorcery|only during your turn")
E.to_csv(sys.argv[1], index=False)
print("cards", len(E), "tagged", int(E.tagged.sum()), "(%.1f%%)" % (100 * E.tagged.mean()))
print("untagged by set:", E[~E.tagged].groupby("set").size().to_dict())
print("slopes: vs A mean %.3f, vs N mean %.3f" % (E.groupby("set").b_A.first().mean(), E.groupby("set").b_N.first().mean()))
for X in ("A", "N"):
    for m in ("gih", "gns", "iwd"):
        z = E.dropna(subset=[f"e0_{m}_{X}", f"e1_{m}_{X}"]); tv = np.cov(z[f"e0_{m}_{X}"], z[f"e1_{m}_{X}"])[0, 1]
        print(f"  {m} vs {X}: n {len(z)}, observed SD {z[f'e_{m}_{X}'].std():.3f}, true SD {np.sqrt(max(tv,0)):.3f}")
