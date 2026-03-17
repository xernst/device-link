"""Generate persona archetype comparison charts."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

# Archetype data from archetypes.py
archetypes = {
    "Skeptic":          {"engage": 0.35, "share": 0.10, "objection": 0.85, "influence": 0.60},
    "Early Adopter":    {"engage": 0.70, "share": 0.60, "objection": 0.15, "influence": 0.70},
    "Pragmatist":       {"engage": 0.40, "share": 0.20, "objection": 0.50, "influence": 0.50},
    "Loyalist":         {"engage": 0.25, "share": 0.15, "objection": 0.70, "influence": 0.40},
    "Influencer":       {"engage": 0.80, "share": 0.75, "objection": 0.25, "influence": 0.90},
    "Lurker":           {"engage": 0.10, "share": 0.02, "objection": 0.05, "influence": 0.10},
    "Budget-Conscious": {"engage": 0.35, "share": 0.25, "objection": 0.60, "influence": 0.40},
    "Expert":           {"engage": 0.45, "share": 0.30, "objection": 0.75, "influence": 0.80},
    "Overwhelmed":      {"engage": 0.15, "share": 0.05, "objection": 0.20, "influence": 0.20},
    "Aspirational":     {"engage": 0.55, "share": 0.45, "objection": 0.15, "influence": 0.50},
}

names = list(archetypes.keys())
metrics = ["engage", "share", "objection", "influence"]

# Color palette
colors = [
    "#ef4444", "#f97316", "#eab308", "#84cc16", "#22c55e",
    "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899", "#f43f5e",
]

fig = plt.figure(figsize=(22, 20), facecolor="#0a0a0a")
gs = GridSpec(3, 5, figure=fig, height_ratios=[1.2, 0.8, 0.8], hspace=0.4, wspace=0.35)

# --- Chart 1: Grouped bar chart (top row, spans all 5 columns) ---
ax1 = fig.add_subplot(gs[0, :])
ax1.set_facecolor("#0a0a0a")

x = np.arange(len(names))
width = 0.2
metric_colors = ["#3b82f6", "#22c55e", "#ef4444", "#eab308"]
metric_labels = ["Engagement Rate", "Share Rate", "Objection Tendency", "Influence Weight"]

for i, (metric, label, color) in enumerate(zip(metrics, metric_labels, metric_colors)):
    values = [archetypes[n][metric] for n in names]
    ax1.bar(x + i * width - 1.5 * width, values, width, label=label, color=color, alpha=0.85, edgecolor="none")

ax1.set_ylabel("Score (0-1)", fontsize=13, color="white", fontweight="bold")
ax1.set_title("Persona Archetypes — Behavioral Profile Comparison", fontsize=20, color="white", fontweight="bold", pad=20)
ax1.set_xticks(x)
ax1.set_xticklabels(names, rotation=30, ha="right", fontsize=12, color="white")
ax1.tick_params(axis="y", colors="white")
ax1.set_ylim(0, 1.05)
ax1.legend(loc="upper right", fontsize=11, facecolor="#1a1a1a", edgecolor="#333", labelcolor="white")
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.spines["left"].set_color("#333")
ax1.spines["bottom"].set_color("#333")
ax1.grid(axis="y", alpha=0.15, color="white")

# --- Chart 2: Radar / spider charts (2 rows of 5) ---
angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
angles += angles[:1]
short_labels = ["Engage", "Share", "Object", "Influence"]

for idx, (name, data) in enumerate(archetypes.items()):
    row = 1 + idx // 5  # rows 1-2
    col = idx % 5
    ax = fig.add_subplot(gs[row, col], polar=True)
    ax.set_facecolor("#0a0a0a")

    values = [data[m] for m in metrics]
    values += values[:1]

    ax.plot(angles, values, "o-", linewidth=2.5, color=colors[idx], markersize=6)
    ax.fill(angles, values, alpha=0.2, color=colors[idx])

    ax.set_ylim(0, 1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(short_labels, fontsize=8, color="#999")
    ax.set_yticks([0.25, 0.5, 0.75])
    ax.set_yticklabels(["", "", ""], fontsize=6)
    ax.tick_params(colors="#555")
    ax.set_title(name, fontsize=12, color=colors[idx], fontweight="bold", pad=14)
    ax.spines["polar"].set_color("#333")
    ax.grid(color="#333", alpha=0.5)

plt.savefig("/home/user/device-link/crowdtest/docs/persona-chart.png", dpi=150, bbox_inches="tight", facecolor="#0a0a0a")
print("Saved to crowdtest/docs/persona-chart.png")
