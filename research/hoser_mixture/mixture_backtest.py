#!/usr/bin/env python3
"""Colour-hoser mixture adjustment (PLAN.md): backtest on the 15 historical hosers, frozen FRA predictions.

  python mixture_backtest.py            # -> result.json, cards.csv, fra_frozen.csv
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "research/production_c3"))
import export_gih_c3_28set as ex  # noqa: E402

g, c3 = ex.g, ex.c3
FIELDS = c3.FIELDS  # removal sweeper bodies cards repeat modal dependency drawback trick sink
SHORT = dict(zip("RSBCPMDXTK", FIELDS))
S = {1: 0.4, 2: 0.7}
BLANK_PP = -8.61
FRA_TARGET = Path("/home/claude/limited-forecast-pages/data/target.json.gz")

# card: (k, live, dead); each version = dict(text=..., mv=..., sym=..., c3={field: value})
CF = {
    ("AFR", "Burning Hands"): (1,
        dict(text="Burning Hands deals 6 damage to target creature or planeswalker.", c3="R2"),
        dict(text="Burning Hands deals 2 damage to target creature or planeswalker.", c3="R1")),
    ("AFR", "Divine Smite"): (1,
        dict(text="Exile target creature or planeswalker an opponent controls.", c3="R2"),
        dict(text="Target creature or planeswalker an opponent controls phases out. (If it phases out, treat it and anything attached to it as though they don't exist until its controller's next turn.)", c3="R1")),
    ("AFR", "Hunter's Mark"): (1,
        dict(text="This spell can't be countered.\nTarget creature you control gets +1/+1 until end of turn. Then it deals damage equal to its power to target creature or planeswalker you don't control.", mv=1, sym=1),
        dict(text="This spell can't be countered.\nTarget creature you control gets +1/+1 until end of turn. Then it deals damage equal to its power to target creature or planeswalker you don't control.", mv=4, sym=2)),
    ("AFR", "Ray of Enfeeblement"): (1,
        dict(text="Target creature gets -4/-4 until end of turn.", c3="R2"),
        dict(text="Target creature gets -4/-1 until end of turn.", c3="R1")),
    ("AFR", "Ray of Frost"): (1,
        dict(text="Flash\nEnchant creature\nWhen this Aura enters, tap enchanted creature.\nEnchanted creature loses all abilities.\nEnchanted creature doesn't untap during its controller's untap step.", c3="R2"),
        dict(text="Flash\nEnchant creature\nEnchanted creature doesn't untap during its controller's untap step.", c3="R1")),
    ("SNC", "Bouncer's Beatdown"): (1,
        dict(text="Bouncer's Beatdown deals X damage to target creature or planeswalker, where X is the greatest power among creatures you control. If that creature or planeswalker would die this turn, exile it instead.", mv=1, sym=1),
        dict(text="Bouncer's Beatdown deals X damage to target creature or planeswalker, where X is the greatest power among creatures you control. If that creature or planeswalker would die this turn, exile it instead.", mv=3, sym=2)),
    ("SNC", "Knockout Blow"): (1,
        dict(text="Knockout Blow deals 4 damage to target attacking or blocking creature and you gain 2 life.", mv=1, sym=1),
        dict(text="Knockout Blow deals 4 damage to target attacking or blocking creature and you gain 2 life.", mv=3, sym=2)),
    ("SNC", "Out of the Way"): (1,
        dict(text="Return target nonland permanent an opponent controls to its owner's hand.\nDraw a card.", mv=2, sym=2),
        dict(text="Return target nonland permanent an opponent controls to its owner's hand.\nDraw a card.", mv=4, sym=2)),
    ("SNC", "Torch Breath"): (1,
        dict(text="This spell can't be countered.\nTorch Breath deals X plus 2 damage to target creature or planeswalker."),
        dict(text="This spell can't be countered.\nTorch Breath deals X damage to target creature or planeswalker.")),
    ("SNC", "Whack"): (1,
        dict(text="Target creature gets -4/-4 until end of turn.", mv=1, sym=1),
        dict(text="Target creature gets -4/-4 until end of turn.", mv=4, sym=2)),
    ("MOM", "Change the Equation"): (2,
        dict(text="Choose one —\n• Counter target spell with mana value 2 or less.\n• Counter target spell with mana value 6 or less."),
        dict(text="Counter target spell with mana value 2 or less.", c3="M0")),
    ("MOM", "Glistening Deluge"): (2,
        dict(text="All creatures get -1/-1 until end of turn. Creatures your opponents control get an additional -2/-2 until end of turn.", c3="R3 S2"),
        dict(text="All creatures get -1/-1 until end of turn.", c3="R1 S1")),
    ("MOM", "Lithomantic Barrage"): (2,
        dict(text="This spell can't be countered.\nLithomantic Barrage deals 5 damage to target creature or planeswalker.", c3="R2"),
        dict(text="This spell can't be countered.\nLithomantic Barrage deals 1 damage to target creature or planeswalker.", c3="R1")),
    ("MOM", "Sandstalker Moloch"): (2,
        dict(text="Flash\nWhen this creature enters, look at the top four cards of your library. You may reveal a permanent card from among them and put it into your hand. Put the rest on the bottom of your library in a random order.", c3="C1 D0"),
        dict(text="Flash", c3="C0 D0")),
    ("MOM", "Surge of Salvation"): (2,
        dict(text="You and permanents you control gain hexproof until end of turn. Prevent all damage that sources your opponents control would deal to creatures you control this turn."),
        dict(text="You and permanents you control gain hexproof until end of turn.")),
}
FRA_CF = {  # name: (unrestricted text, C3 change)
    "Essence Burn": ("Essence Burn deals 5 damage to target creature or planeswalker. If that permanent would die this turn, exile it instead.", "R2"),
    "Flourishing Grapple": ("Target creature or planeswalker an opponent controls loses all abilities until end of turn. Target creature you control deals damage equal to its power to that permanent.", "R1"),
    "Refute Destiny": ("Exile target creature or planeswalker. Surveil 1. (Look at the top card of your library. You may put it into your graveyard.)", "R2"),
    "Precise Redaction": ("Counter target spell.", "R1"),
    "Terminal Criticism": ("Destroy target creature or planeswalker. You gain 1 life.", "R2"),
}
RARITY = {0: "common", 1: "uncommon", 2: "rare", 3: "mythic"}


def card_dict(row, text, mv, sym):
    has_x = int(row["has_x_cost"])
    pw = row.get("power"); tg = row.get("toughness")
    return {"name": row["name"], "oracle_text": text, "type_line": row["type_line"], "cmc": mv,
            "rarity": RARITY[int(row["rarity_ord"])], "colors": [c for c in "WUBRG" if row[f"color_{c}"] == 1],
            "mana_cost": "{X}" * has_x + "{C}" * (int(sym) - has_x),
            "power": None if pd.isna(pw) else str(int(pw)), "toughness": None if pd.isna(tg) else str(int(tg))}


def c3_raw_of(row):
    raw = pd.read_csv(c3.C3_OUT, keep_default_na=False).set_index("key")
    return raw


def variant(row, base, cols, raw_row, text, mv=None, sym=None, change=""):
    mv = float(row["mv"]) if mv is None else float(mv)
    sym = int(row["mana_symbols"]) if sym is None else int(sym)
    f = ex.card_features(card_dict(row, text, mv, sym))
    out = row.copy()
    for k, v in f.items():
        if k in out.index and k not in ("name", "collector_number"):
            out[k] = v
    out["__text"] = g.text_of(pd.DataFrame([{"oracle_text": text, "type_line": row["type_line"]}])).iloc[0]
    r = {fld: raw_row[fld] for fld in FIELDS}
    r["dep"] = raw_row["dep"]
    for tok in change.split():
        r[SHORT[tok[0]]] = int(tok[1:])
    x = pd.DataFrame([{**{k: int(v) for k, v in r.items() if k != "dep"}, "dep": r["dep"]}])
    cc = c3.c3_columns(x, pd.Series([mv]))
    for c in cols:
        out[c] = float(cc[c].iloc[0])
    return out


def main():
    pool, base, cols = ex.training()
    raws = pd.concat([pd.read_csv(c3.C3_OUT, keep_default_na=False),
                      pd.read_csv(ROOT / "research/case6/c3_features_new.csv.gz", keep_default_na=False)]).set_index("key")
    nums = base + cols
    rows, results = [], {}
    for s in ("AFR", "SNC", "MOM"):
        cards = [(k, v) for k, v in CF.items() if k[0] == s]
        frame = []
        for (st, name), (kk, live, dead) in cards:
            row = pool[(pool["set"] == st) & (pool["name"] == name)].iloc[0]
            raw_row = raws.loc[f"{st}|{name}"]
            # Reconstruction check: the real text must reproduce the stored features.
            orig = variant(row, base, cols, raw_row, row["oracle_text"])
            diff = [c for c in base if not (pd.isna(orig[c]) and pd.isna(row[c])) and abs(float(orig[c]) - float(row[c])) > 1e-9]
            if diff:
                raise SystemExit(f"reconstruction mismatch for {name}: {diff}")
            frame += [row, variant(row, base, cols, raw_row, live["text"], live.get("mv"), live.get("sym"), live.get("c3", "")),
                      variant(row, base, cols, raw_row, dead["text"], dead.get("mv"), dead.get("sym"), dead.get("c3", ""))]
        test = pd.DataFrame(frame).reset_index(drop=True)
        train = pool[pool["set"] != s]
        p = ex.predict(train, test, nums)[3] * 100
        for i, ((st, name), (kk, live, dead)) in enumerate(cards):
            cur, lv, dd = p[3 * i], p[3 * i + 1], p[3 * i + 2]
            actual = float(pool[(pool["set"] == st) & (pool["name"] == name)]["actual_gih"].iloc[0]) * 100
            adj = S[kk] * lv + (1 - S[kk]) * dd
            rows.append({"set": st, "card": name, "k": kk, "s": S[kk], "actual": actual, "current": cur, "live": lv, "dead": dd, "adjusted": adj})
        print(s, "done", flush=True)
    d = pd.DataFrame(rows)
    d["err_current"] = d["current"] - d["actual"]
    d["err_adjusted"] = d["adjusted"] - d["actual"]
    per_set = d.groupby("set").apply(lambda x: pd.Series({"mae_current": x.err_current.abs().mean(), "mae_adjusted": x.err_adjusted.abs().mean(),
                                                          "bias_current": x.err_current.mean(), "bias_adjusted": x.err_adjusted.mean()}))
    res = {"s": S, "blank_pp": BLANK_PP, "n_cards": len(d),
           "mae_current": float(d.err_current.abs().mean()), "mae_adjusted": float(d.err_adjusted.abs().mean()),
           "bias_current": float(d.err_current.mean()), "bias_adjusted": float(d.err_adjusted.mean()),
           "mae_live_only": float((d.live - d.actual).abs().mean()), "mae_dead_only": float((d.dead - d.actual).abs().mean()),
           "per_set": per_set.to_dict(orient="index")}
    wins = int((per_set.mae_adjusted < per_set.mae_current).sum())
    res["rule_H"] = {"1_mae_improves": res["mae_adjusted"] < res["mae_current"], "2_set_wins": wins, "pass": bool(res["mae_adjusted"] < res["mae_current"] and wins >= 2)}
    # Within-set metrics of the three sets with the adjusted cards swapped in (OOF predictions from production_c3).
    oof = pd.read_csv(ex.OOF)
    sw = oof.copy()
    for r in rows:
        m = (sw["set"] == r["set"]) & (sw["name"] == r["card"])
        sw.loc[m, "pred"] = r["adjusted"] / 100
    for label, frame in (("current", oof), ("adjusted", sw)):
        sub = frame[frame["set"].isin(["AFR", "SNC", "MOM"])]
        summ, per = g.within_set(sub, sub["pred"].to_numpy())
        res[f"within_set_{label}"] = {"mae_pp": summ["mae_pp"], "spearman": summ["spearman"]}
    # FRA (only type), frozen.
    fra, f = ex.fra_frame(FRA_TARGET, base, cols, pool)
    fra_rows, fra_frame = [], []
    for i, card in enumerate(fra):
        if card["name"] in FRA_CF:
            row = f.iloc[i].copy()
            row["name"] = card["name"]; row["has_x_cost"] = row.get("has_x_cost", 0)
            text, change = FRA_CF[card["name"]]
            raw_row = raws.loc[f"FRA|{card['id']}"]
            fra_rows.append((i, card))
            fra_frame += [row, variant(row, base, cols, raw_row, c3.normalize({**card, "oracle_text": text})["oracle_text"], change=change)]
    t = pd.DataFrame(fra_frame).reset_index(drop=True)
    p = ex.predict(pool, t, nums)[3] * 100
    adopted = {c["id"]: c for c in json.loads(gzip.open("/home/claude/limited-forecast-pages/data/adopted-gih-fra.json.gz", "rt").read())["cards"]}
    set_mean = float(np.mean([c["gih"] for c in adopted.values()]))
    out = []
    for j, (i, card) in enumerate(fra_rows):
        cur, unr = p[2 * j], p[2 * j + 1]
        adj = S[2] * unr + (1 - S[2]) * (set_mean + BLANK_PP)
        out.append({"id": card["id"], "name": card["name"], "published": adopted[card["id"]]["gih"], "current_rerun": cur,
                    "unrestricted": unr, "adjusted": adj, "set_pred_mean": set_mean})
    fz = pd.DataFrame(out)
    fz.round(4).to_csv(HERE / "fra_frozen.csv", index=False)
    res["fra"] = fz.round(4).to_dict(orient="records")
    d.round(4).to_csv(HERE / "cards.csv", index=False)
    (HERE / "result.json").write_text(json.dumps(res, indent=2, default=float))
    print(d.round(2).to_string(index=False))
    print(json.dumps({k: res[k] for k in ("mae_current", "mae_adjusted", "bias_current", "bias_adjusted", "mae_live_only", "mae_dead_only", "rule_H",
                                          "within_set_current", "within_set_adjusted")}, indent=1, default=float))
    print(fz.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
