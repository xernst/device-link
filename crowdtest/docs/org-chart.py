"""Generate CrowdTest Paperclip org chart visualization."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(1, 1, figsize=(18, 12), facecolor="#0a0a0a")
ax.set_facecolor("#0a0a0a")
ax.set_xlim(0, 18)
ax.set_ylim(0, 12)
ax.axis("off")

# Agent definitions: (x, y, title, role, color, budget, heartbeat)
agents = [
    (9, 10,   "CEO",             "Strategy & Delegation",     "#ef4444", "$10/mo", "30m"),
    (4, 7.5,  "Product Designer","UI/UX Design",              "#a855f7", "$4/mo",  "30m"),
    (13, 7.5, "CTO",             "Architecture & Review",     "#3b82f6", "$5/mo",  "30m"),
    (8, 4.5,  "Backend Engineer","Simulation Engine & API",   "#22c55e", "$8/mo",  "15m"),
    (13, 4.5, "Frontend Engineer","Dashboard & Social Feed",  "#06b6d4", "$8/mo",  "15m"),
    (5, 1.5,  "LLM Engineer",    "Prompts & AI Layer",       "#eab308", "$6/mo",  "20m"),
    (11, 1.5, "QA Engineer",     "Testing & Validation",     "#f97316", "$4/mo",  "20m"),
]

# Draw connection lines first
line_color = "#333333"
lw = 2

# CEO to Designer
ax.plot([9, 4], [9.5, 8.3], color=line_color, linewidth=lw, zorder=1)
# CEO to CTO
ax.plot([9, 13], [9.5, 8.3], color=line_color, linewidth=lw, zorder=1)
# CTO to Backend
ax.plot([13, 8], [6.7, 5.3], color=line_color, linewidth=lw, zorder=1)
# CTO to Frontend
ax.plot([13, 13], [6.7, 5.3], color=line_color, linewidth=lw, zorder=1)
# CTO to LLM
ax.plot([13, 5], [6.7, 2.3], color=line_color, linewidth=lw, zorder=1)
# CTO to QA
ax.plot([13, 11], [6.7, 2.3], color=line_color, linewidth=lw, zorder=1)

# Draw agent boxes
for x, y, title, role, color, budget, heartbeat in agents:
    # Box
    box = FancyBboxPatch(
        (x - 2.2, y - 0.8), 4.4, 1.6,
        boxstyle="round,pad=0.15",
        facecolor="#1a1a1a",
        edgecolor=color,
        linewidth=2.5,
        zorder=2,
    )
    ax.add_patch(box)

    # Title
    ax.text(x, y + 0.35, title, fontsize=13, fontweight="bold", color=color,
            ha="center", va="center", zorder=3)
    # Role
    ax.text(x, y - 0.05, role, fontsize=9, color="#999999",
            ha="center", va="center", zorder=3)
    # Budget + Heartbeat
    ax.text(x, y - 0.45, f"{budget}  ·  {heartbeat} heartbeat", fontsize=8, color="#666666",
            ha="center", va="center", zorder=3)

# Title
ax.text(9, 11.5, "CrowdTest — Paperclip Agent Org Chart", fontsize=20,
        fontweight="bold", color="white", ha="center", va="center")

# Adapter label
ax.text(9, 0.3, "All agents: Claude Code adapter  ·  Total budget: $50/mo  ·  Embedded PGlite database",
        fontsize=10, color="#555555", ha="center", va="center")

# Phase badges
phases = [
    (2, 3.5, "Phase 1: Core Engine", "#22c55e"),
    (9, 3.5, "Phase 2: API + Frontend", "#3b82f6"),
    (15.5, 3.5, "Phase 3: Polish + Launch", "#eab308"),
]
for px, py, label, pcolor in phases:
    ax.text(px, py, label, fontsize=8, color=pcolor, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#111111", edgecolor=pcolor, linewidth=1))

plt.savefig("/home/user/device-link/crowdtest/docs/org-chart.png",
            dpi=150, bbox_inches="tight", facecolor="#0a0a0a")
print("Saved to crowdtest/docs/org-chart.png")
