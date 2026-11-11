"""Are there a few cards with LARGE top-player-specific effects that average statistics hide?
Exploratory. Builds on card_level_skill.py (same residual e = top_c - b * nontop_c, halves split by draft_id).
1. Tail test: compare observed |z| and replicated-tail counts with what a NORMAL distribution of true effects
   (SD from the half covariance) would produce. More extremes than that = heavy tail (a few big cards).
2. Kurtosis of the true effects from independent halves (normal = 3).
3. Empirical Bayes per card with two priors: normal (shrinks extremes hard) and a nonparametric prior
   (NPMLE on a grid, no shape assumed). Each prior is fitted on one half and checked on the other half.
Usage: python3 top_specific_tail.py <case6 data dir> <set_cards.csv.gz> <oof_B11g.csv.gz> <out.csv>"""
import pandas as pd, numpy as np, glob, json, sys
from scipy.stats import norm, pearsonr, spearmanr
D = sys.argv[1]; rng = np.random.default_rng(7)
fr = [pd.read_csv(f) for f in sorted(glob.glob(D + "/*_case6_28d.csv")) if json.load(open(f.replace("_28d.csv", "_manifest.json")))["has_user_wr_bucket"]]
A = pd.concat(fr); A = A[A.top60n50_games >= 500].reset_index(drop=True)
for h in ("", "_h0", "_h1"):
    tg, tw = A[f"top60n50{h}_games"], A[f"top60n50{h}_wins"]; ng, nw = A[f"all{h}_games"] - tg, A[f"all{h}_wins"] - tw
    A["top" + h], A["nt" + h] = 100 * tw / tg, 100 * nw / ng
    A["v_top" + h] = A["top" + h] * (100 - A["top" + h]) / tg; A["v_nt" + h] = A["nt" + h] * (100 - A["nt" + h]) / ng
    for c in ("top" + h, "nt" + h): A[c + "_c"] = A[c] - A.groupby("set")[c].transform("mean")
b = np.polyfit(A.nt_c, A.top_c, 1)[0]
for h in ("", "_h0", "_h1"):
    A["e" + h] = A["top" + h + "_c"] - b * A["nt" + h + "_c"]; A["v" + h] = A["v_top" + h] + b * b * A["v_nt" + h]
infl = ((A.e_h0 - A.e_h1) ** 2).mean() / 4 / A.v.mean()
for h in ("", "_h0", "_h1"): A["v" + h] *= infl
tv = np.cov(A.e_h0, A.e_h1)[0, 1]; tsd = np.sqrt(tv)
basic = A.card_name.isin(["Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"])
print(f"cards {len(A)} (basic lands {basic.sum()}), slope {b:.3f}, noise inflation {infl:.3f}, true SD {tsd:.3f}")

# ---------- 1. tail test against a normal true distribution
def sim_counts(true_draw, reps=400):
    out = []
    for _ in range(reps):
        t = true_draw(len(A))
        e0 = t + rng.normal(0, np.sqrt(A.v_h0)); e1 = t + rng.normal(0, np.sqrt(A.v_h1)); e = t + rng.normal(0, np.sqrt(A.v))
        z = e / np.sqrt(A.v); z0 = e0 / np.sqrt(A.v_h0); z1 = e1 / np.sqrt(A.v_h1)
        out.append([(np.abs(z) > 3).sum(), (np.abs(z) > 4).sum(), ((z0 > 2) & (z1 > 2)).sum(), ((z0 < -2) & (z1 < -2)).sum(), ((z0 > 2.5) & (z1 > 2.5)).sum() + ((z0 < -2.5) & (z1 < -2.5)).sum()])
    return np.array(out)
z = A.e / np.sqrt(A.v); z0 = A.e_h0 / np.sqrt(A.v_h0); z1 = A.e_h1 / np.sqrt(A.v_h1)
obs = [(z.abs() > 3).sum(), (z.abs() > 4).sum(), ((z0 > 2) & (z1 > 2)).sum(), ((z0 < -2) & (z1 < -2)).sum(), ((z0 > 2.5) & (z1 > 2.5)).sum() + ((z0 < -2.5) & (z1 < -2.5)).sum()]
labels = ["|z|>3", "|z|>4", "both halves z>2", "both halves z<-2", "both halves |z|>2.5 same sign"]
sn = sim_counts(lambda n: np.zeros(n)); sg = sim_counts(lambda n: rng.normal(0, tsd, n))
print("\n1. tail counts: observed | expected if no real effect | expected if real effects are NORMAL with SD %.2f (95%% range)" % tsd)
for i, l in enumerate(labels):
    print(f"  {l:32s} {obs[i]:4d} | {sn[:, i].mean():6.1f} | {sg[:, i].mean():6.1f} ({np.percentile(sg[:, i], 2.5):.0f}-{np.percentile(sg[:, i], 97.5):.0f})")

# ---------- 2. kurtosis of true effects from independent halves (high-information cards, where it is identifiable)
def kurt(x):
    p = x.e_h0 * x.e_h1; m2 = p.mean()
    m4 = (p ** 2).mean() - (m2 * (x.v_h0 + x.v_h1)).mean() - (x.v_h0 * x.v_h1).mean()
    return m2, m4 / m2 ** 2
sets = A.set.unique()
for lab, m in (("all cards", np.ones(len(A), bool)), ("top games >= 2000", A.top60n50_games >= 2000), ("top games >= 5000", A.top60n50_games >= 5000)):
    x = A[m]; m2, k = kurt(x); bs = []
    for _ in range(1000):
        ss = rng.choice(sets, len(sets)); y = pd.concat([x[x.set == s] for s in ss]); bs.append(kurt(y)[1])
    print(f"2. kurtosis of true effects ({lab}, n {len(x)}): {k:.2f} (set bootstrap 95% {np.percentile(bs, 2.5):.2f}-{np.percentile(bs, 97.5):.2f}); normal = 3")

# ---------- 3. empirical Bayes: normal prior vs nonparametric prior, fitted on one half, checked on the other
grid = np.linspace(-6, 6, 241)
def npmle(e, v, iters=600):
    w = np.full(len(grid), 1 / len(grid)); L = norm.pdf((e[:, None] - grid[None, :]) / np.sqrt(v)[:, None]) / np.sqrt(v)[:, None]
    for _ in range(iters):
        P = L * w; P /= P.sum(1, keepdims=True); w = P.mean(0)
    return w
def post_np(e, v, w):
    L = norm.pdf((e[:, None] - grid[None, :]) / np.sqrt(v)[:, None]) * w; L /= L.sum(1, keepdims=True)
    return L @ grid, L
def post_n(e, v, s2): return e * s2 / (s2 + v)
res = {}
for a, bb in (("_h0", "_h1"), ("_h1", "_h0")):
    ea, va, eb = A["e" + a].to_numpy(), A["v" + a].to_numpy(), A["e" + bb].to_numpy()
    s2 = max(np.var(ea) - va.mean(), 1e-6)  # normal prior variance from this half alone
    w = npmle(ea, va); pn = post_n(ea, va, s2); pp, _ = post_np(ea, va, w)
    for k, p in (("normal", pn), ("nonparametric", pp)):
        r = res.setdefault(k, {"slope": [], "mse": [], "top1pct_pred": [], "top1pct_other": [], "bot1pct_pred": [], "bot1pct_other": []})
        r["slope"].append(np.polyfit(p, eb, 1)[0]); r["mse"].append(((eb - p) ** 2 - A["v" + bb]).mean())
        hi = p >= np.quantile(p, .99); lo = p <= np.quantile(p, .01)
        r["top1pct_pred"].append(p[hi].mean()); r["top1pct_other"].append(eb[hi].mean()); r["bot1pct_pred"].append(p[lo].mean()); r["bot1pct_other"].append(eb[lo].mean())
print("\n3. per-card estimates fitted on one half, checked on the other (averaged over both directions)")
print("   calibration slope: 1 = right size, >1 = estimates too shrunk ('rounded'), <1 = too large")
for k, r in res.items():
    print(f"  {k:14s} slope {np.mean(r['slope']):.2f} | error vs truth (MSE, noise removed) {np.mean(r['mse']):.3f} | top 1%: estimate {np.mean(r['top1pct_pred']):+.2f}, other half {np.mean(r['top1pct_other']):+.2f} | bottom 1%: estimate {np.mean(r['bot1pct_pred']):+.2f}, other half {np.mean(r['bot1pct_other']):+.2f}")
# final estimates on the full data with the nonparametric prior
w = npmle(A.e.to_numpy(), A.v.to_numpy(), 1000); pm, P = post_np(A.e.to_numpy(), A.v.to_numpy(), w)
A["est"] = pm; A["p_gt1"] = P[:, grid > 1].sum(1); A["p_lt_m1"] = P[:, grid < -1].sum(1)
A["est_normal"] = post_n(A.e, A.v, tv)
mass = lambda lo, hi: w[(grid > lo) & (grid <= hi)].sum()
print("\n   nonparametric prior (full data): share of cards with true effect")
print("   <= -2: %.2f%%, -2..-1: %.2f%%, -1..-0.5: %.1f%%, -0.5..0.5: %.1f%%, 0.5..1: %.1f%%, 1..2: %.2f%%, > 2: %.2f%%" % tuple(100 * mass(*r) for r in ((-9, -2), (-2, -1), (-1, -.5), (-.5, .5), (.5, 1), (1, 2), (2, 9))))
nb = ~basic
print("   cards (excluding basic lands) with estimate >= +1.0pp: %d, >= +0.75pp: %d, <= -1.0pp: %d, <= -0.75pp: %d; P(true > +1pp) >= 0.5: %d" % (
    (A.est[nb] >= 1).sum(), (A.est[nb] >= .75).sum(), (A.est[nb] <= -1).sum(), (A.est[nb] <= -.75).sum(), (A.p_gt1[nb] >= .5).sum()))

# ---------- 4. reprints: does the same card show the same top-specific effect in different sets?
nb_A = A[nb]
g = nb_A.groupby("card_name").filter(lambda x: x.set.nunique() >= 2)
pairs = []
for n_, x in g.groupby("card_name"):
    x = x.sort_values("set").reset_index(drop=True)
    for i in range(len(x)):
        for j in range(i + 1, len(x)): pairs.append((x.e[i], x.e[j], x.v[i], x.v[j]))
P2 = np.array(pairs)
if len(P2):
    c = np.mean(P2[:, 0] * P2[:, 1]); print(f"\n4. reprints (same name in 2+ sets, no basic lands): {g.card_name.nunique()} cards, {len(P2)} pairs; covariance of e across sets {c:.3f} (true variance within a set {tv:.3f}); correlation {pearsonr(P2[:, 0], P2[:, 1])[0]:.3f}")

# ---------- 5. relation to the overall model's misses (B11g) and to known bombs
o = pd.read_csv(sys.argv[3]).rename(columns={"name": "card_name"}); o["miss"] = 100 * (o.actual_gih - o.pred); o["miss"] -= o.groupby("set").miss.transform("mean")
A = A.merge(o[["set", "card_name", "miss", "rarity_ord"]], on=["set", "card_name"], how="left")
ok = A.miss.notna()
print(f"\n5. B11g miss (actual - prediction, overall GIH) vs top-specific estimate: Pearson {pearsonr(A[ok].miss, A[ok].est)[0]:.3f}, n {ok.sum()}")
u = A[ok & (A.miss > 6)]; print(f"   cards B11g under-predicts by > 6pp: n {len(u)}, mean top-specific estimate {u.est.mean():+.2f}pp (all cards {A[ok].est.mean():+.2f})")
for s, nme in (("MSH", "Avengers Assemble!"), ("ECL", "Chronicle of Victory"), ("LTR", "Orcish Bowmasters"), ("SOS", "Together as One"), ("LCI", "Zoetic Glyph")):
    r = A[(A.set == s) & (A.card_name == nme)]
    if len(r): r = r.iloc[0]; print(f"   {s} {nme}: overall-model miss {r.miss:+.1f}, raw top-specific {r.e:+.2f} (z {r.e/np.sqrt(r.v):+.2f}), estimate {r.est:+.2f}, top games {int(r.top60n50_games)}")
    else: print(f"   {s} {nme}: not in the >=500 top-game set")
C = pd.read_csv(sys.argv[2]); C["set"] = C.key.str.split("|").str[0]; C["card_name"] = C.key.str.split("|", n=1).str[1]
A = A.merge(C[["set", "card_name", "type", "mv", "colors"]], on=["set", "card_name"], how="left")
cols = ["set", "card_name", "rarity_ord", "type", "colors", "nt_c", "e", "est", "est_normal", "p_gt1", "p_lt_m1", "top60n50_games"]
print("\nlargest positive estimates (top players clearly better), no basic lands:"); print(A[~A.card_name.isin(["Plains", "Island", "Swamp", "Mountain", "Forest"])].nlargest(25, "est")[cols].round(2).to_string(index=False))
print("\nlargest negative estimates (top players clearly worse), no basic lands:"); print(A[~A.card_name.isin(["Plains", "Island", "Swamp", "Mountain", "Forest"])].nsmallest(15, "est")[cols].round(2).to_string(index=False))
A[cols + ["e_h0", "e_h1", "v"]].to_csv(sys.argv[4], index=False)
