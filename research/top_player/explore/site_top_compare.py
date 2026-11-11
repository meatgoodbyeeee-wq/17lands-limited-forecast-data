"""Compare the 17Lands site "Top" user group (api/card_data, ALL_TIME) with the Case 6 public-data aggregates.
Exploratory. Usage: python3 site_top_compare.py <case6 data dir> <site_top_cards.csv> [oof_B11g.csv.gz]"""
import pandas as pd, numpy as np, glob, json, sys
from scipy.stats import spearmanr, pearsonr
D, F = sys.argv[1], sys.argv[2]
site = pd.read_csv(F)
oof = pd.read_csv(sys.argv[3]).rename(columns={"name": "card_name", "pred": "b11g"}) if len(sys.argv) > 3 else None
rows, pool = [], []
for s, x in site.groupby("set"):
    p = pd.read_csv(f"{D}/{s}_case6_28d.csv"); man = json.load(open(f"{D}/{s}_case6_manifest.json"))
    m = x.merge(p.drop(columns="set"), left_on="name", right_on="card_name")
    m = m[(m.top60n50_games >= 500) & (m.top_gih_n >= 500)].copy()
    m["site_top"] = 100 * m.top_gih_wr; m["site_all"] = 100 * m.all_gih_wr
    m["pub_all"] = 100 * m.all_wins / m.all_games
    for g in ("top56n50", "top60n50", "top64n50"):
        m[g] = 100 * m[g + "_wins"] / m[g + "_games"].where(m[g + "_games"] > 0)
    m["se2_site"] = m.site_top * (100 - m.site_top) / m.top_gih_n
    m["se2_60"] = m.top60n50 * (100 - m.top60n50) / m.top60n50_games
    cols = ["site_top", "site_all", "pub_all", "top56n50", "top60n50", "top64n50"]
    for c in cols: m[c + "_c"] = m[c] - m[c].mean()
    rel_site = 1 - m.se2_site.mean() / m.site_top.var(); rel_60 = 1 - m.se2_60.mean() / m.top60n50.var()
    r = pearsonr(m.site_top, m.top60n50)[0]
    ok64 = m[m.top64n50_games >= 500]
    d = dict(set=s, n=len(m), n_pub_top=int((p.top60n50_games >= 500).sum()),
             site_top_share=x.top_gih_n.sum() / x.all_gih_n.sum(), pub_top_share=man["group_games"]["top60n50"] / man["group_games"]["all"],
             alltime_over_28d_games=m.all_gih_n.sum() / m.all_games.sum(),
             ctl_pearson_all=pearsonr(m.site_all, m.pub_all)[0], ctl_mean_diff=(m.site_all - m.pub_all).mean(), ctl_mad_c=(m.site_all_c - m.pub_all_c).abs().mean(),
             gap_site=(m.site_top - m.site_all).mean(), gap_60=(m.top60n50 - m.pub_all).mean(), gap_56=(m.top56n50 - m.pub_all).mean(), gap_64=(ok64.top64n50 - ok64.pub_all).mean(),
             sd_site=m.site_top.std(), sd_60=m.top60n50.std(), sd_site_all=m.site_all.std(),
             slope_site_on_all=np.polyfit(m.site_all_c, m.site_top_c, 1)[0], slope_60_on_all=np.polyfit(m.pub_all_c, m.top60n50_c, 1)[0],
             sp_site_60=spearmanr(m.site_top, m.top60n50)[0], pe_site_60=r, pe_site_56=pearsonr(m.site_top, m.top56n50)[0], pe_site_64=pearsonr(ok64.site_top, ok64.top64n50)[0],
             sp_site_all=spearmanr(m.site_top, m.site_all)[0], sp_60_all=spearmanr(m.top60n50, m.pub_all)[0],
             slope_site_on_60=np.polyfit(m.top60n50_c, m.site_top_c, 1)[0], mad_c=(m.site_top_c - m.top60n50_c).abs().mean(),
             rel_site=rel_site, rel_60=rel_60, disatt=r / np.sqrt(rel_site * rel_60),
             noise_sd_expected=np.sqrt(m.se2_site.mean() + m.se2_60.mean()), diff_sd=(m.site_top_c - m.top60n50_c).std(),
             med_games_site=m.top_gih_n.median(), med_games_60=m.top60n50_games.median())
    rows.append(d); pool.append(m)
R = pd.DataFrame(rows)
pd.set_option("display.width", 260); pd.set_option("display.max_columns", 60)
print(R[["set", "n", "site_top_share", "pub_top_share", "alltime_over_28d_games", "ctl_pearson_all", "gap_site", "gap_60", "sd_site", "sd_60", "slope_site_on_all", "slope_60_on_all", "sp_site_60", "pe_site_60", "disatt", "sp_site_all", "sp_60_all", "mad_c", "diff_sd", "noise_sd_expected"]].round(3).to_string(index=False))
print("MEAN", R.drop(columns="set").mean().round(3).to_dict())
P = pd.concat(pool)
if oof is not None:
    z = P.merge(oof[["set", "card_name", "b11g"]], on=["set", "card_name"]).copy()
    z["p_c"] = 100 * (z.b11g - z.groupby("set").b11g.transform("mean"))
    for c in ("site_top", "top60n50", "site_all", "pub_all"): z[c + "_c"] = z[c] - z.groupby("set")[c].transform("mean")
    out = {}
    for tgt in ("site_top_c", "top60n50_c"):
        mk, sp, orc = [], [], []
        ref = "site_all_c" if tgt == "site_top_c" else "pub_all_c"
        for s in z.set.unique():
            tr, te = z[z.set != s], z[z.set == s]
            k = (tr.p_c * tr[tgt]).sum() / (tr.p_c ** 2).sum(); b = (tr[ref] * tr[tgt]).sum() / (tr[ref] ** 2).sum()
            mk.append((k * te.p_c - te[tgt]).abs().mean()); sp.append(spearmanr(te.p_c, te[tgt])[0]); orc.append((b * te[ref] - te[tgt]).abs().mean())
        out[tgt] = dict(k=round(k, 3), mae=round(np.mean(mk), 3), spearman=round(np.mean(sp), 3), oracle_mae=round(np.mean(orc), 3))
    print("B11g x k on the same cards:", len(z), out)
P[["set", "card_name", "site_top", "site_all", "pub_all", "top60n50", "top_gih_n", "top60n50_games"]].to_csv(sys.argv[4] if len(sys.argv) > 4 else "/dev/null", index=False)
