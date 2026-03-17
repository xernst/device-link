"""Generate worldview dimensions chart — all 7 dimensions with their modifiers."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

# All worldview dimensions and their modifiers with key trust scores
dimensions = {
    "Political": {
        "Progressive":    {"corporate": -0.2, "social_proof": 0.1, "sustainability": 0.3, "tradition": 0.0},
        "Moderate Left":  {"corporate": 0.0,  "social_proof": 0.1, "sustainability": 0.15, "tradition": 0.0},
        "Centrist":       {"corporate": 0.05, "social_proof": 0.1, "sustainability": 0.0, "tradition": 0.0},
        "Moderate Right": {"corporate": 0.1,  "social_proof": 0.0, "sustainability": 0.0, "tradition": 0.1},
        "Conservative":   {"corporate": 0.1,  "social_proof": 0.0, "sustainability": -0.1, "tradition": 0.25},
        "Libertarian":    {"corporate": -0.15,"social_proof": 0.0, "sustainability": 0.0, "tradition": 0.0},
        "Apolitical":     {"corporate": 0.0,  "social_proof": 0.1, "sustainability": 0.0, "tradition": 0.0},
    },
    "Religious": {
        "Secular":        {"science": 0.2,  "faith": -0.2, "moral": -0.1, "community": 0.0},
        "Spiritual":      {"science": 0.0,  "faith": 0.0,  "moral": 0.0,  "community": 0.1},
        "Mainstream":     {"science": 0.0,  "faith": 0.1,  "moral": 0.1,  "community": 0.15},
        "Devout":         {"science": 0.0,  "faith": 0.3,  "moral": 0.25, "community": 0.15},
    },
    "Cultural": {
        "Individualist":  {"personal": 0.25, "social_proof": -0.15, "global": 0.0,  "heritage": 0.0},
        "Collectivist":   {"personal": 0.0,  "social_proof": 0.25,  "global": 0.0,  "heritage": 0.0},
        "Traditionalist": {"personal": 0.0,  "social_proof": 0.0,   "global": -0.1, "heritage": 0.25},
        "Cosmopolitan":   {"personal": 0.0,  "social_proof": 0.0,   "global": 0.2,  "heritage": 0.0},
        "Multicultural":  {"personal": 0.0,  "social_proof": 0.0,   "global": 0.1,  "heritage": 0.2},
    },
    "Economic": {
        "Free Market":    {"premium": 0.15, "ethical": 0.0,  "minimalism": 0.0,  "status": 0.1},
        "Conscious Cap.": {"premium": 0.0,  "ethical": 0.25, "minimalism": 0.0,  "status": 0.0},
        "Anti-Consumer":  {"premium": -0.2, "ethical": 0.15, "minimalism": 0.2,  "status": -0.3},
        "Aspiring Aff.":  {"premium": 0.25, "ethical": 0.0,  "minimalism": -0.1, "status": 0.2},
    },
    "Media Diet": {
        "Mainstream":     {"expert": 0.2,  "grassroots": -0.05, "data": 0.1,  "viral": 0.0},
        "Alternative":    {"expert": -0.1, "grassroots": 0.2,   "data": 0.0,  "viral": 0.0},
        "Academic":       {"expert": 0.15, "grassroots": 0.0,   "data": 0.25, "viral": -0.15},
        "Social Native":  {"expert": 0.0,  "grassroots": 0.1,   "data": 0.0,  "viral": 0.15},
        "News Avoidant":  {"expert": 0.0,  "grassroots": 0.0,   "data": 0.0,  "viral": -0.2},
    },
    "Trust": {
        "Institution":    {"brand": 0.25,  "peers": 0.0,  "self": 0.0,  "anti_auth": 0.0},
        "Peer-Trusting":  {"brand": 0.0,   "peers": 0.3,  "self": 0.0,  "anti_auth": 0.0},
        "Self-Reliant":   {"brand": -0.1,  "peers": 0.0,  "self": 0.25, "anti_auth": 0.0},
        "Auth-Skeptical": {"brand": -0.2,  "peers": 0.0,  "self": 0.1,  "anti_auth": 0.25},
    },
    "Generational": {
        "Gen Z":          {"authenticity": 0.25, "corporate_cringe": -0.3, "mental_health": 0.2, "stability": 0.0},
        "Millennial":     {"authenticity": 0.15, "corporate_cringe": -0.1, "mental_health": 0.1, "stability": 0.1},
        "Gen X":          {"authenticity": 0.1,  "corporate_cringe": -0.1, "mental_health": 0.0, "stability": 0.2},
        "Boomer":         {"authenticity": 0.0,  "corporate_cringe": 0.0,  "mental_health": 0.0, "stability": 0.25},
    },
}

# Color scheme per dimension
dim_colors = {
    "Political": "#3b82f6",
    "Religious": "#a855f7",
    "Cultural": "#22c55e",
    "Economic": "#eab308",
    "Media Diet": "#06b6d4",
    "Trust": "#ef4444",
    "Generational": "#f97316",
}

fig = plt.figure(figsize=(24, 28), facecolor="#0a0a0a")
gs = GridSpec(4, 2, figure=fig, hspace=0.35, wspace=0.3)

dim_list = list(dimensions.items())

for idx, (dim_name, modifiers) in enumerate(dim_list):
    row = idx // 2
    col = idx % 2
    ax = fig.add_subplot(gs[row, col])
    ax.set_facecolor("#111111")

    mod_names = list(modifiers.keys())
    factors = list(list(modifiers.values())[0].keys())
    n_mods = len(mod_names)
    n_factors = len(factors)

    x = np.arange(n_mods)
    width = 0.8 / n_factors

    factor_colors = ["#3b82f6", "#22c55e", "#ef4444", "#eab308"]

    for i, factor in enumerate(factors):
        values = [modifiers[m][factor] for m in mod_names]
        bars = ax.bar(
            x + i * width - (n_factors - 1) * width / 2,
            values, width,
            label=factor,
            color=factor_colors[i % len(factor_colors)],
            alpha=0.85,
            edgecolor="none",
        )

    ax.set_title(dim_name, fontsize=16, color=dim_colors[dim_name], fontweight="bold", pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(mod_names, rotation=25, ha="right", fontsize=10, color="white")
    ax.tick_params(axis="y", colors="white")
    ax.set_ylim(-0.4, 0.4)
    ax.axhline(y=0, color="#444", linewidth=0.8)
    ax.legend(fontsize=8, facecolor="#1a1a1a", edgecolor="#333", labelcolor="white", loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#333")
    ax.spines["bottom"].set_color("#333")
    ax.grid(axis="y", alpha=0.1, color="white")
    ax.set_ylabel("Trust modifier", fontsize=10, color="#999")

# Use the 8th slot for the dimension overview / legend
ax_overview = fig.add_subplot(gs[3, 1])
ax_overview.set_facecolor("#111111")
ax_overview.set_xlim(0, 10)
ax_overview.set_ylim(0, 10)
ax_overview.axis("off")

overview_text = (
    "7 Dimensions × 35 Modifiers\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "Each persona gets ONE modifier\n"
    "per dimension (7 total).\n\n"
    "Modifiers shift trust in different\n"
    "message types: positive values\n"
    "increase receptivity, negative\n"
    "values increase resistance.\n\n"
    "Combined with psychographic\n"
    "archetypes, this creates\n"
    "thousands of unique persona\n"
    "combinations — each with\n"
    "distinct reaction patterns."
)
ax_overview.text(
    5, 5, overview_text,
    fontsize=13, color="white",
    ha="center", va="center",
    family="monospace",
    bbox=dict(boxstyle="round,pad=1", facecolor="#1a1a1a", edgecolor="#333"),
)

fig.suptitle(
    "CrowdTest — Worldview Dimensions & Trust Modifiers",
    fontsize=22, color="white", fontweight="bold", y=0.98,
)

plt.savefig(
    "/home/user/device-link/crowdtest/docs/worldview-chart.png",
    dpi=150, bbox_inches="tight", facecolor="#0a0a0a",
)
print("Saved to crowdtest/docs/worldview-chart.png")
