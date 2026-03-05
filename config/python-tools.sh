#!/usr/bin/env bash
# Device Link — Install Python tools on a helper Mac.
# Creative tools (pitch decks, docs, visuals) + quant tools (math, stats, SQL).
#
# Creative:
#   python-pptx  — PowerPoint / pitch deck creation
#   python-docx  — Word document creation
#   Pillow       — Image processing and generation
#   matplotlib   — Charts and graphs
#   cairosvg     — SVG rendering to PNG/PDF
#
# Quant / Math / SQL:
#   numpy        — Numerical computing
#   scipy        — Scientific computing (stats, optimization)
#   pandas       — Data manipulation and time series
#   statsmodels  — Statistical models (ARIMA, regression, tests)
#   sympy        — Symbolic math (calculus, algebra, exact solutions)
#   sqlalchemy   — SQL toolkit (connect to any database)
#   duckdb       — Embedded analytical SQL (query CSV/Parquet directly)
#
# Usage:
#   bash config/python-tools.sh

set -euo pipefail

echo ""
echo "=== Python Tools (Creative + Quant) ==="
echo ""

# --- Ensure Python 3 ---

if ! command -v python3 &>/dev/null; then
    echo "  Installing Python 3..."
    brew install python
fi

PYTHON_VER=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo "  Python: $PYTHON_VER"

# --- Install creative packages ---

echo ""
echo "  Installing creative tools..."
pip3 install --quiet python-pptx python-docx Pillow matplotlib cairosvg 2>&1 | tail -3

# --- Install quant packages ---

echo "  Installing quant/math/SQL tools..."
pip3 install --quiet numpy scipy pandas statsmodels sympy sqlalchemy duckdb 2>&1 | tail -3

# --- Verify ---

echo ""
echo "  Verifying installations..."
FAILED=0

VERIFY_PKGS=(
    "pptx:python-pptx"
    "docx:python-docx"
    "PIL:Pillow"
    "matplotlib:matplotlib"
    "cairosvg:cairosvg"
    "numpy:numpy"
    "scipy:scipy"
    "pandas:pandas"
    "statsmodels:statsmodels"
    "sympy:sympy"
    "sqlalchemy:sqlalchemy"
    "duckdb:duckdb"
)

for entry in "${VERIFY_PKGS[@]}"; do
    mod="${entry%%:*}"
    name="${entry##*:}"
    if python3 -c "import ${mod}" 2>/dev/null; then
        echo "    $name — ok"
    else
        echo "    $name — FAILED"
        ((FAILED++))
    fi
done

if [[ $FAILED -gt 0 ]]; then
    echo ""
    echo "  Warning: $FAILED packages failed to install" >&2
fi

# --- Summary ---

echo ""
echo "=== Python Tools Ready ==="
echo ""
echo "  Creative:"
echo "    python-pptx  — from pptx import Presentation"
echo "    python-docx  — from docx import Document"
echo "    Pillow       — from PIL import Image"
echo "    matplotlib   — import matplotlib.pyplot as plt"
echo "    cairosvg     — import cairosvg"
echo ""
echo "  Quant / Math:"
echo "    numpy        — import numpy as np"
echo "    scipy        — from scipy import stats, optimize"
echo "    pandas       — import pandas as pd"
echo "    statsmodels  — import statsmodels.api as sm"
echo "    sympy        — from sympy import symbols, solve, diff"
echo ""
echo "  SQL:"
echo "    duckdb       — import duckdb; duckdb.sql(\"SELECT * FROM 'data.csv'\")"
echo "    sqlalchemy   — from sqlalchemy import create_engine"
echo ""
