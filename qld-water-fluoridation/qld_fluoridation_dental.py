"""
Water fluoridation and dental hospitalisations in regional Queensland

Since 2012 each Queensland council decides whether to fluoridate its water
supply. Roughly 50 of 77 councils now have no fluoridated supply, most of them
outside the south-east. This script tests whether that shows up in potentially
preventable hospitalisations (PPH) for dental conditions, and what else
explains the variation between areas.

Unit of analysis: ABS Statistical Area Level 3 (SA3), 82 areas in Queensland.

Inputs (data/):
  aihw_dental_pph_sa3_qld.csv      AIHW, PPH by small geographic areas,
                                   dental conditions, 2020-21 and 2021-22
  sa3_lga_population_2021.csv      ABS 2021 Census mesh block counts rolled up
                                   to SA3 x council, with SEIFA IRSD and
                                   remoteness (see build notes in README)
  lga_no_fluoridation_qh_2022.csv  Queensland Health list of councils with no
                                   natural or added fluoride (Dec 2022)
  qh_dental_waiting_hhs_june.csv   Queensland Health public dental waiting
                                   lists, June snapshot each year 2016-2025

Run:
  python qld_fluoridation_dental.py

Outputs:
  data/sa3_analysis_dataset.csv, images/*.png and a printed summary.
"""
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RNG = np.random.default_rng(2027)
N_BOOT = 2000
QLD_CENSUS_2021 = 5_156_828          # ABS published usual residents, Qld
QH_NOT_FLUORIDATED_SHARE = 0.28      # Queensland Health, Dec 2022 (~28%)

# Council -> Hospital and Health Service. HHS boundaries follow council
# boundaries outside Brisbane and Scenic Rim, which are split at SA3 level below.
HHS_COUNCILS = {
    "Torres and Cape": ["Aurukun", "Cook", "Hope Vale", "Kowanyama", "Lockhart River",
                        "Mapoon", "Napranum", "Northern Peninsula Area", "Pormpuraaw",
                        "Torres", "Torres Strait Island", "Weipa", "Wujal Wujal"],
    "Cairns and Hinterland": ["Cairns", "Cassowary Coast", "Croydon", "Douglas",
                              "Etheridge", "Mareeba", "Tablelands", "Yarrabah"],
    "Townsville": ["Townsville", "Burdekin", "Charters Towers", "Hinchinbrook",
                   "Palm Island", "Flinders (Qld)", "Richmond"],
    "North West": ["Mount Isa", "Cloncurry", "Burke", "Carpentaria", "Doomadgee",
                   "Mornington", "McKinlay"],
    "Mackay": ["Mackay", "Isaac", "Whitsunday"],
    "Central West": ["Barcaldine", "Barcoo", "Blackall Tambo", "Boulia", "Diamantina",
                     "Longreach", "Winton"],
    "Central Queensland": ["Rockhampton", "Livingstone", "Gladstone", "Banana",
                           "Central Highlands (Qld)", "Woorabinda"],
    "Wide Bay": ["Bundaberg", "Fraser Coast", "North Burnett"],
    "Sunshine Coast": ["Sunshine Coast", "Noosa", "Gympie"],
    "Darling Downs": ["Toowoomba", "Southern Downs", "Goondiwindi", "Western Downs",
                      "South Burnett", "Cherbourg"],
    "South West": ["Balonne", "Bulloo", "Maranoa", "Murweh", "Paroo", "Quilpie"],
    "West Moreton": ["Ipswich", "Lockyer Valley", "Somerset"],
    "Gold Coast": ["Gold Coast"],
    "Metro North": ["Moreton Bay"],
    "Metro South": ["Logan", "Redland"],
}
# Brisbane and Scenic Rim SA3s, assigned to the HHS that covers most residents.
SA3_HHS_OVERRIDE = {
    30101: "Metro South", 30102: "Metro South", 30103: "Metro South",
    30201: "Metro North", 30202: "Metro North", 30203: "Metro North", 30204: "Metro North",
    30301: "Metro South", 30302: "Metro South", 30303: "Metro South", 30304: "Metro South",
    30305: "Metro South", 30306: "Metro South",
    30401: "Metro South", 30402: "Metro North", 30403: "Metro North", 30404: "Metro North",
    30501: "Metro North", 30502: "Metro South", 30503: "Metro North", 30504: "Metro North",
    30904: "Gold Coast", 31001: "Metro South", 31002: "West Moreton", 31101: "Metro South",
}
SEQ_HHS = {"Metro North", "Metro South", "Gold Coast", "Sunshine Coast", "West Moreton"}


def clean_council(name):
    """Queensland Health uses full council titles; ABS uses the short name."""
    name = re.sub(r" (Aboriginal Shire|Regional|Shire|City) Council$", "", name)
    return name.replace("Blackall-Tambo", "Blackall Tambo")


def wls(y, X, w):
    """Weighted least squares. Returns coefficients and weighted R-squared."""
    sw = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    resid = y - X @ beta
    ybar = np.average(y, weights=w)
    r2 = 1 - np.sum(w * resid**2) / np.sum(w * (y - ybar) ** 2)
    return beta, r2


def build_sa3(pph, pop, no_fl):
    pop = pop.copy()
    pop["no_fluoride"] = pop["lga_name"].isin(no_fl)
    council_hhs = {c: h for h, cs in HHS_COUNCILS.items() for c in cs}

    p = pop.assign(
        p_nofl=pop.persons * pop.no_fluoride,
        irsd_x_p=pop.persons * pop.irsd_wmean,
        hhs=pop.lga_name.map(council_hhs),
    )
    sa3 = p.groupby("sa3_code").agg(
        persons=("persons", "sum"), p_nofl=("p_nofl", "sum"), irsd_x_p=("irsd_x_p", "sum"),
        p_major=("persons_major", "sum"), p_inner=("persons_inner", "sum"),
        p_outer=("persons_outer", "sum"), p_remote=("persons_remote", "sum"),
    )
    sa3["share_no_fluoride"] = sa3.p_nofl / sa3.persons
    sa3["irsd"] = sa3.irsd_x_p / sa3.persons
    for c in ["major", "inner", "outer", "remote"]:
        sa3[f"share_{c}"] = sa3[f"p_{c}"] / sa3.persons

    # HHS by majority of residents, then the Brisbane / Scenic Rim overrides
    top = p.dropna(subset=["hhs"]).groupby(["sa3_code", "hhs"]).persons.sum().reset_index()
    top = top.sort_values("persons").drop_duplicates("sa3_code", keep="last").set_index("sa3_code").hhs
    sa3["hhs"] = top
    for code, h in SA3_HHS_OVERRIDE.items():
        sa3.loc[code, "hhs"] = h

    # Two-year average of the age-standardised rate; counts summed
    rate = pph.groupby("sa3_code").agg(
        sa3_name=("sa3_name", "first"), pph_rate=("pph_rate_asr", "mean"),
        pph_count=("pph_count", "sum"), years=("pph_rate_asr", "count"),
    )
    out = rate.join(sa3, how="inner")
    out["exposure"] = pd.cut(out.share_no_fluoride, [-0.01, 0.05, 0.95, 1.01],
                             labels=["Fluoridated", "Mixed", "Not fluoridated"])
    out["band"] = np.select([out.share_major > 0.5, out.share_inner > 0.5],
                            ["Major city", "Inner regional"], "Outer regional & remote")
    out["seq"] = out.hhs.isin(SEQ_HHS)
    return out


def design(d, with_controls=True, with_hhs=False, with_fluoride=True):
    cols, names = [np.ones(len(d))], ["const"]
    if with_fluoride:
        cols.append(d.share_no_fluoride.values); names.append("share_no_fluoride")
    if with_controls:
        cols += [((d.irsd - 1000) / 50).values, d.share_inner.values,
                 (d.share_outer + d.share_remote).values]
        names += ["irsd_per_half_sd", "share_inner", "share_outer_remote"]
    if with_hhs:
        for h in sorted(d.hhs.unique())[1:]:
            cols.append((d.hhs == h).astype(float).values); names.append(f"hhs_{h}")
    return np.column_stack(cols), names


def bootstrap_effect(d, with_hhs):
    """90% interval for the fluoridation effect, resampling SA3s."""
    effects = []
    for _ in range(N_BOOT):
        s = d.iloc[RNG.integers(0, len(d), len(d))]
        X, _ = design(s, with_hhs=with_hhs)
        if np.linalg.matrix_rank(X) < X.shape[1]:
            continue
        b, _ = wls(np.log(s.pph_rate.values), X, s.persons.values)
        effects.append(np.exp(b[1]) - 1)
    return np.percentile(effects, [5, 95])


def waiting_summary(wl):
    ga = wl[wl.list == "GA"].copy()
    ga["region"] = np.where(ga.hhs.isin(SEQ_HHS), "South-east", "Regional")
    trend = ga.groupby(["year", "region"])[["waiting", "waiting_overdue"]].sum()
    trend["pct_overdue"] = trend.waiting_overdue / trend.waiting
    latest = ga[ga.year == ga.year.max()].set_index("hhs")
    latest["pct_overdue"] = latest.waiting_overdue / latest.waiting
    return trend.reset_index(), latest


def chart_pph(d, hhs_rates, path):
    """One row per HHS, one dot per SA3, coloured by water supply status."""
    ink, muted, grid = "#0b0b0b", "#6b6a66", "#e6e5e1"
    colours = {"Fluoridated": "#2a78d6", "Mixed": "#1baf7a", "Not fluoridated": "#eb6834"}
    order = hhs_rates.sort_values("pph_rate").index.tolist()
    fig, ax = plt.subplots(figsize=(10, 6.4), dpi=150)
    for i, h in enumerate(order):
        g = d[d.hhs == h]
        ax.plot([g.pph_rate.min(), g.pph_rate.max()], [i, i], color=grid, linewidth=2, zorder=1)
        for exp, gg in g.groupby("exposure", observed=True):
            ax.scatter(gg.pph_rate, [i] * len(gg), s=np.clip(np.sqrt(gg.persons) / 2.5, 18, 200),
                       color=colours[exp], edgecolor="white", linewidth=1.2, zorder=3)
        ax.text(905, i, f"{hhs_rates.loc[h, 'pph_rate']:.0f}", va="center", ha="right",
                fontsize=8.5, color=ink)
    ax.text(905, len(order) - 0.3, "HHS rate", va="bottom", ha="right", fontsize=8.5, color=muted)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=9, color=ink)
    ax.set_xlim(150, 910)
    ax.set_ylim(-0.7, len(order) - 0.1)
    ax.set_xlabel("Dental PPH per 100,000, age-standardised, average of 2020-21 and 2021-22", color=muted)
    ax.grid(axis="x", color=grid, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(grid)
    ax.tick_params(colors=muted, length=0)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, markersize=8, label=l)
               for l, c in colours.items()]
    ax.legend(handles=handles, frameon=False, loc="lower right", bbox_to_anchor=(0.93, 0.0), fontsize=9,
              title="SA3 water supply (council level)", title_fontsize=9)
    ax.set_title("Dental hospitalisation rates cluster by health service, whatever the water supply\n"
                 "Each dot is an SA3; dot size shows population", loc="left", fontsize=12, color=ink)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def chart_ga(trend, latest, path):
    ink, muted, grid = "#0b0b0b", "#6b6a66", "#e6e5e1"
    colours = {"South-east": "#2a78d6", "Regional": "#eb6834"}
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5.2), dpi=150,
                                 gridspec_kw={"width_ratios": [1, 1.15]})
    for reg, g in trend.groupby("region"):
        a1.plot(g.year, g.waiting, color=colours[reg], linewidth=2, marker="o", markersize=5, label=reg)
        last = g.iloc[-1]
        a1.annotate(f"{int(last.waiting):,}", (last.year, last.waiting), xytext=(6, -3),
                    textcoords="offset points", fontsize=8.5, color=ink)
    a1.set_title("People waiting for dental treatment under\ngeneral anaesthetic, June each year",
                 loc="left", fontsize=11, color=ink)
    a1.legend(frameon=False, fontsize=9)
    a1.set_xticks(range(2016, 2026, 2))

    lt = latest[latest.waiting >= 50].sort_values("pct_overdue")
    cols = [colours["South-east"] if h in SEQ_HHS else colours["Regional"] for h in lt.index]
    a2.barh(lt.index, lt.pct_overdue * 100, color=cols, height=0.62)
    for i, (h, r) in enumerate(lt.iterrows()):
        a2.text(r.pct_overdue * 100 + 1.2, i, f"{r.pct_overdue:.0%} of {int(r.waiting):,}",
                va="center", fontsize=8.5, color=ink)
    a2.set_xlim(0, 100)
    a2.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c, label=l) for l, c in colours.items()],
              frameon=False, fontsize=9, loc="lower right")
    a1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    a2.set_title("Share past the clinically recommended time,\nJune 2025 (HHSs with 50+ waiting)",
                 loc="left", fontsize=11, color=ink)
    for ax in (a1, a2):
        ax.grid(axis="x" if ax is a2 else "y", color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ["top", "right"]:
            ax.spines[s].set_visible(False)
        for s in ["left", "bottom"]:
            ax.spines[s].set_color(grid)
        ax.tick_params(colors=muted)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    pph = pd.read_csv("data/aihw_dental_pph_sa3_qld.csv")
    pop = pd.read_csv("data/sa3_lga_population_2021.csv")
    no_fl = set(pd.read_csv("data/lga_no_fluoridation_qh_2022.csv").lga_name_qh.map(clean_council))
    wl = pd.read_csv("data/qh_dental_waiting_hhs_june.csv")

    print("== Validation")
    unmatched = no_fl - set(pop.lga_name)
    assert not unmatched, f"Councils not found in ABS names: {unmatched}"
    print(f"All {len(no_fl)} Queensland Health councils match an ABS 2021 LGA")
    total = pop.persons.sum()
    print(f"Residents allocated: {total:,} vs {QLD_CENSUS_2021:,} published "
          f"({total / QLD_CENSUS_2021:.2%}; the gap is 'no usual address' and offshore, excluded)")
    share = pop.loc[pop.lga_name.isin(no_fl), "persons"].sum() / total
    print(f"Residents in a council with no fluoridated supply: {share:.1%} "
          f"(Queensland Health: ~{QH_NOT_FLUORIDATED_SHARE:.0%} without fluoridated water)")

    d = build_sa3(pph, pop, no_fl)
    assert d.hhs.notna().all()
    np_rows = pph.pph_rate_asr.isna().sum()
    print(f"SA3s analysed: {len(d)} (both years published for {int((d.years == 2).sum())}); "
          f"suppressed rows: {np_rows}")
    d.round(4).to_csv("data/sa3_analysis_dataset.csv")

    print("\n== Rate by exposure group (population-weighted)")
    def wavg(g):
        return pd.Series({"sa3s": len(g), "residents": g.persons.sum(),
                          "pph_rate": np.average(g.pph_rate, weights=g.persons)})
    print(d.groupby("exposure", observed=True).apply(wavg).round(0).to_string())
    print("\nWithin remoteness band:")
    print(d.groupby(["band", "exposure"], observed=True).apply(wavg).round(0).to_string())
    print("\nRegional Queensland only (outside the five south-east HHSs):")
    print(d[~d.seq].groupby("exposure", observed=True).apply(wavg).round(0).to_string())

    print("\n== Weighted regression on log rate")
    y, w = np.log(d.pph_rate.values), d.persons.values
    models = {
        "Fluoridation only": dict(with_controls=False),
        "Fluoridation + SEIFA + remoteness": dict(),
        "HHS only": dict(with_controls=False, with_hhs=True, with_fluoride=False),
        "All of the above": dict(with_hhs=True),
    }
    r2 = {}
    for name, kw in models.items():
        X, cols = design(d, **kw)
        b, r2[name] = wls(y, X, w)
        eff = f", fluoridation effect {np.exp(b[1]) - 1:+.0%}" if "share_no_fluoride" in cols else ""
        print(f"{name:36s} R2 = {r2[name]:.2f}{eff}")
    lo, hi = bootstrap_effect(d, with_hhs=False)
    print(f"Effect of 100% vs 0% non-fluoridated, with controls: 90% interval {lo:+.0%} to {hi:+.0%}")
    lo2, hi2 = bootstrap_effect(d, with_hhs=True)
    print(f"Same, comparing SA3s within the same HHS:          90% interval {lo2:+.0%} to {hi2:+.0%}")

    print("\n== Highest and lowest HHSs (population-weighted dental PPH)")
    hhs = d.groupby("hhs").apply(wavg).sort_values("pph_rate", ascending=False)
    hhs["share_no_fluoride"] = d.groupby("hhs").apply(lambda g: np.average(g.share_no_fluoride, weights=g.persons))
    print(hhs.round(2).to_string())

    print("\n== General anaesthetic waiting list (June)")
    trend, latest = waiting_summary(wl)
    print(trend.round(2).to_string(index=False))
    print(latest.sort_values("pct_overdue", ascending=False)[["waiting", "waiting_overdue", "pct_overdue"]].round(2).to_string())

    chart_pph(d, hhs, "images/dental_pph_by_hhs.png")
    chart_ga(trend, latest, "images/ga_waiting_list.png")
    print("\nCharts saved to images/")


if __name__ == "__main__":
    main()
