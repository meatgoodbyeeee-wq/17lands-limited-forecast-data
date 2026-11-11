"""Card-level check: are there cards that top players use clearly better (or worse) than the linear scaling says?
Exploratory. Usage: python3 card_level_skill.py <case6 data dir> <set_cards.csv.gz> [site_top_cards.csv] [out.csv]"""
import pandas as pd, numpy as np, glob, json, sys, re
from scipy.stats import norm, pearsonr
D = sys.argv[1]
fr = []
for f in sorted(glob.glob(D + "/*_case6_28d.csv")):
    if json.load(open(f.replace("_28d.csv", "_manifest.json")))["has_user_wr_bucket"]:
        fr.append(pd.read_csv(f))
A = pd.concat(fr); A = A[A.top60n50_games >= 500].copy()
def rate(w, g): return 100 * w / g
for h, suf in (("", ""), ("_h0", "_h0"), ("_h1", "_h1")):
    tg, tw = A[f"top60n50{suf}_games"], A[f"top60n50{suf}_wins"]
    ng, nw = A[f"all{suf}_games"] - tg, A[f"all{suf}_wins"] - tw
    A["top" + h], A["nt" + h] = rate(tw, tg), rate(nw, ng)
    A["v_top" + h] = A["top" + h] * (100 - A["top" + h]) / tg; A["v_nt" + h] = A["nt" + h] * (100 - A["nt" + h]) / ng
    for c in ("top" + h, "nt" + h): A[c + "_c"] = A[c] - A.groupby("set")[c].transform("mean")
b = np.polyfit(A.nt_c, A.top_c, 1)[0]
for h in ("", "_h0", "_h1"):
    A["e" + h] = A["top" + h + "_c"] - b * A["nt" + h + "_c"]
    A["v_e" + h] = A["v_top" + h] + b * b * A["v_nt" + h]
print(f"cards {len(A)}, sets {A.set.nunique()}, pooled slope top on non-top {b:.3f}")
# --- noise calibration and true variance from independent halves
noise_emp = ((A.e_h0 - A.e_h1) ** 2).mean() / 4; noise_bin = A.v_e.mean()
infl = noise_emp / noise_bin
true_var = np.cov(A.e_h0, A.e_h1)[0, 1]
print(f"residual e: SD {A.e.std():.3f} | noise var empirical {noise_emp:.3f} (SD {noise_emp**.5:.3f}) vs binomial {noise_bin:.3f} -> inflation {infl:.3f}")
print(f"true variance (cov of halves) {true_var:.3f} -> true SD {max(true_var,0)**.5:.3f}; share of observed variance {true_var/A.e.var():.3f}")
bs = []
rng = np.random.default_rng(1); sets = A.set.unique()
for _ in range(2000):
    ss = rng.choice(sets, len(sets)); x = pd.concat([A[A.set == s] for s in ss]); bs.append(np.cov(x.e_h0, x.e_h1)[0, 1])
print("  set-bootstrap 95% CI of true SD:", np.round(np.sqrt(np.clip(np.percentile(bs, [2.5, 97.5]), 0, None)), 3))
for lab, m in (("top games 500-1999", A.top60n50_games < 2000), ("2000-4999", (A.top60n50_games >= 2000) & (A.top60n50_games < 5000)), (">=5000", A.top60n50_games >= 5000)):
    x = A[m]; tv = np.cov(x.e_h0, x.e_h1)[0, 1]
    print(f"  {lab}: n {len(x)}, observed SD {x.e.std():.3f}, true SD {max(tv,0)**.5:.3f}, noise SD {(((x.e_h0-x.e_h1)**2).mean()/4)**.5:.3f}")
# --- z scores (calibrated) and tails
A["se"] = np.sqrt(A.v_e * infl); A["z"] = A.e / A.se
for h in ("_h0", "_h1"): A["z" + h] = A["e" + h] / np.sqrt(A["v_e" + h] * infl)
n = len(A)
print("full-sample z: SD %.3f; share |z|>2 %.2f%% (normal 4.55%%), >3 %.2f%% (0.27%%), >4 %.3f%% (0.006%%)" % (A.z.std(), 100 * (A.z.abs() > 2).mean(), 100 * (A.z.abs() > 3).mean(), 100 * (A.z.abs() > 4).mean()))
print("  counts: |z|>3: %d (expected %.1f), |z|>4: %d (expected %.2f); positive >3: %d, negative <-3: %d" % ((A.z.abs() > 3).sum(), n * 0.0027, (A.z.abs() > 4).sum(), n * 6.3e-5, (A.z > 3).sum(), (A.z < -3).sum()))
for t in (1.5, 2.0):
    p = 1 - norm.cdf(t)
    print(f"  both halves z>{t}: {((A.z_h0 > t) & (A.z_h1 > t)).sum()} (expected by chance {n*p*p:.1f}); both z<-{t}: {((A.z_h0 < -t) & (A.z_h1 < -t)).sum()} (expected {n*p*p:.1f}); opposite signs beyond {t}: {(((A.z_h0 > t) & (A.z_h1 < -t)) | ((A.z_h0 < -t) & (A.z_h1 > t))).sum()} (expected {2*n*p*p:.1f})")
# --- tail replication: select on one half, read the other
def rep(sel_col, read_col, lo, hi):
    x = A[(A[sel_col] >= lo) & (A[sel_col] < hi)]
    return len(x), x[sel_col.replace("z", "e")].mean(), x[read_col].mean()
print("replication (select by z in one half, read residual in the other half; both directions averaged):")
for lo, hi in ((-9, -3), (-3, -2), (-2, -1), (-1, 1), (1, 2), (2, 3), (3, 9)):
    a = rep("z_h0", "e_h1", lo, hi); c = rep("z_h1", "e_h0", lo, hi)
    nn = a[0] + c[0]; sel = (a[0] * a[1] + c[0] * c[1]) / max(nn, 1); rd = (a[0] * a[2] + c[0] * c[2]) / max(nn, 1)
    print(f"  z in [{lo},{hi}): n {nn}, selected-half mean {sel:+.2f}pp, other-half mean {rd:+.2f}pp, ratio {rd/sel if abs(sel)>1e-9 else float('nan'):.2f}")
# --- nonlinearity of top vs non-top
A["bin"] = A.groupby("set").nt_c.transform(lambda s: pd.qcut(s, 10, labels=False))
print("mean residual by decile of non-top strength (0 = weakest):", A.groupby("bin").e.mean().round(2).tolist())
# --- categories
C = pd.read_csv(sys.argv[2]); C["set"] = C.key.str.split("|").str[0]; C["card_name"] = C.key.str.split("|", n=1).str[1]
A = A.merge(C[["set", "card_name", "type", "text", "mv", "colors", "rar"]], on=["set", "card_name"], how="left")
print("type matched", A.type.notna().sum(), "of", len(A))
t = A.type.fillna(""); tx = A.text.fillna("").str.lower()
cat = {
 "creature": t.str.contains("Creature"), "instant": t.str.contains("Instant"), "sorcery": t.str.contains("Sorcery"),
 "aura": t.str.contains("Aura"), "equipment": t.str.contains("Equipment"),
 "other enchantment": t.str.contains("Enchantment") & ~t.str.contains("Creature|Aura"), "other artifact": t.str.contains("Artifact") & ~t.str.contains("Creature|Equipment"),
 "land": t.str.contains("Land"), "planeswalker": t.str.contains("Planeswalker"),
 "counterspell": tx.str.contains("counter target"), "flash": tx.str.contains(r"\bflash\b"), "draws cards": tx.str.contains(r"draw (?:a|two|three|x) card"),
 "combat trick (instant, +N/+N)": t.str.contains("Instant") & tx.str.contains(r"gets? \+\d/\+\d"),
 "removal-like (destroy/exile/damage to target)": tx.str.contains(r"destroy target|exile target|damage to (?:any )?target"),
 "sacrifice": tx.str.contains("sacrifice"), "discard": tx.str.contains("discard"), "graveyard": tx.str.contains("graveyard"),
 "mana value <=2": A.mv <= 2, "mana value >=6": A.mv >= 6, "multicolor": A.colors.fillna("").str.len() >= 2,
 "common": A.rar == 0, "uncommon": A.rar == 1, "rare": A.rar == 2, "mythic": A.rar == 3,
}
rows = []
for k, m in cat.items():
    m = m.fillna(False) & A.type.notna(); x = A[m]
    if len(x) < 30: continue
    # per-set means to get a set-level SE
    ps = x.groupby("set").e.mean(); rows.append(dict(category=k, n=len(x), mean_e=x.e.mean(), se_sets=ps.std() / np.sqrt(len(ps)), sets_same_sign=int((np.sign(ps) == np.sign(x.e.mean())).sum()), n_sets=len(ps), h0=x.e_h0.mean(), h1=x.e_h1.mean()))
R = pd.DataFrame(rows); R["t"] = R.mean_e / R.se_sets
pd.set_option("display.width", 220); print(R.sort_values("mean_e").round(3).to_string(index=False))
# --- candidate list: replicated in both halves
if len(sys.argv) > 3:
    s = pd.read_csv(sys.argv[3]); s["site_top"] = 100 * s.top_gih_wr; s["site_all"] = 100 * s.all_gih_wr
    s = s[s.top_gih_n >= 500]
    A = A.merge(s[["set", "name", "site_top", "site_all", "top_gih_n"]], left_on=["set", "card_name"], right_on=["set", "name"], how="left")
    for c in ("site_top", "site_all"): A[c + "_c"] = A[c] - A.groupby("set")[c].transform("mean")
    ok = A.site_top_c.notna(); bsite = np.polyfit(A[ok].site_all_c, A[ok].site_top_c, 1)[0]
    A["e_site"] = A.site_top_c - bsite * A.site_all_c
    print(f"site Top residual (slope {bsite:.3f}) vs public residual: Pearson {pearsonr(A[ok].e, A[ok].e_site)[0]:.3f} (shares games; not independent)")
cols = ["set", "card_name", "rar", "type", "mv", "nt_c", "top_c", "e", "z", "z_h0", "z_h1", "top60n50_games"] + (["e_site"] if "e_site" in A else [])
pos = A[(A.z_h0 > 1.5) & (A.z_h1 > 1.5)].sort_values("z", ascending=False); neg = A[(A.z_h0 < -1.5) & (A.z_h1 < -1.5)].sort_values("z")
print("\nTOP PLAYERS DO BETTER (both halves z>1.5):", len(pos)); print(pos[cols].head(30).round(2).to_string(index=False))
print("\nTOP PLAYERS DO WORSE (both halves z<-1.5):", len(neg)); print(neg[cols].head(30).round(2).to_string(index=False))
if "e_site" in A:
    print("site residual of the replicated cards: better-group mean %+.2f (n %d), worse-group mean %+.2f (n %d)" % (pos.e_site.mean(), pos.e_site.notna().sum(), neg.e_site.mean(), neg.e_site.notna().sum()))
if len(sys.argv) > 4: A[cols + ["se"]].to_csv(sys.argv[4], index=False)
