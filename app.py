"""
app.py
======
CBBI Strategy Lab — Streamlit entry point and home page.

Responsibilities:
  1. Page config + global CSS
  2. Numba JIT warmup on startup
  3. Home page content (nav cards, project description, disclaimer)
"""

import streamlit as st
from core.data_loader import load_master_dataset, load_research_results
from core.engine import warmup_numba

# ── Page configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CBBI Strategy Lab",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "CBBI Strategy Lab — Bitcoin backtesting simulator built on academic research. Not financial advice.",
    },
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Google Fonts: Neo-Brutalist dual-font stack ── */
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Work+Sans:wght@300;400;500;600&family=Inter:wght@400;500;600&display=swap');

  /* ── Base reset ── */
  html, body, [class*="css"] {
    font-family: 'Work Sans', sans-serif;
    letter-spacing: -0.01em;
    background-color: #fff8f1;
    color: #213448;
  }
  .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1280px; }

  /* ── Typography: Editorial hierarchy ── */
  h1, h2, h3, h4 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.03em !important;
    font-weight: 700 !important;
    color: #213448 !important;
  }

  /* ── Metric cards: Neo-Brutalist light edition ── */
  [data-testid="metric-container"] {
    background: #ffffff;
    border: 2px solid #d4cdc4;
    border-radius: 0px !important;
    padding: 1.1rem 1.2rem;
    box-shadow: 4px 4px 0px 0px rgba(33, 52, 72, 0.18);
    transition: box-shadow 0.15s, transform 0.15s;
  }
  [data-testid="metric-container"]:hover {
    box-shadow: 6px 6px 0px 0px rgba(33, 52, 72, 0.28);
    transform: translate(-1px, -1px);
  }
  [data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.7rem !important;
    color: #547792 !important;
    opacity: 1 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    font-weight: 600 !important;
  }
  [data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.04em !important;
    line-height: 1.1 !important;
    color: #213448 !important;
  }

  /* ── Nav cards: Hard-shadow brutalist (light) ── */
  .nav-card {
    background: #ffffff;
    border: 2px solid #c9c2b8;
    border-radius: 0px;
    padding: 2rem;
    text-align: center;
    cursor: pointer;
    min-height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.8rem;
    box-shadow: 5px 5px 0px 0px rgba(33, 52, 72, 0.15);
    transition: box-shadow 0.15s, transform 0.15s;
  }
  .nav-card:hover {
    border-color: #0a7c6e;
    box-shadow: 7px 7px 0px 0px rgba(10, 124, 110, 0.25);
    transform: translate(-2px, -2px);
  }
  .nav-card .icon { font-size: 2.5rem; }
  .nav-card h3 {
    margin: 0;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.15rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #213448;
  }
  .nav-card p {
    margin: 0;
    font-size: 0.83rem;
    color: #547792;
    line-height: 1.55;
    font-family: 'Work Sans', sans-serif;
  }

  /* ── Disclaimer box ── */
  .disclaimer-box {
    background: #fff5f5;
    border: 2px solid rgba(220, 60, 60, 0.35);
    border-radius: 0px;
    padding: 0.9rem 1.3rem;
    font-size: 0.82rem;
    color: #5a1a1a;
    line-height: 1.65;
    box-shadow: 3px 3px 0px 0px rgba(220, 60, 60, 0.12);
  }

  /* ── Info strip ── */
  .info-strip {
    background: #edf4f7;
    border: 2px solid #94b4c1;
    border-radius: 0px;
    padding: 0.5rem 1rem;
    font-size: 0.82rem;
    color: #213448;
    box-shadow: 2px 2px 0px 0px rgba(84, 119, 146, 0.2);
  }

  /* ── Section labels ── */
  .section-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #547792;
    opacity: 1;
    margin-bottom: 0.4rem;
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: #ede8e0;
    border-right: 2px solid #c9c2b8;
  }

  /* ── Buttons: Tactile Neo-Brutalism (light) ── */
  .stButton > button {
    border-radius: 0px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    border: 2px solid #213448 !important;
    background: #ffffff !important;
    color: #213448 !important;
    box-shadow: 3px 3px 0px 0px rgba(33, 52, 72, 0.2) !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
  }
  .stButton > button:hover {
    transform: translate(-2px, -2px) !important;
    box-shadow: 5px 5px 0px 0px rgba(33, 52, 72, 0.3) !important;
    border-color: #0a7c6e !important;
    color: #0a7c6e !important;
  }
  .stButton > button:active {
    transform: translate(2px, 2px) !important;
    box-shadow: 0px 0px 0px 0px !important;
  }
  .stButton > button[kind="primary"] {
    background: #0a7c6e !important;
    border: 2px solid #0a7c6e !important;
    color: #ffffff !important;
    box-shadow: 4px 4px 0px 0px rgba(10, 124, 110, 0.35) !important;
    width: 100%;
    padding: 0.65rem;
    font-size: 1rem;
  }
  .stButton > button[kind="primary"]:hover {
    background: #085f54 !important;
    box-shadow: 6px 6px 0px 0px rgba(10, 124, 110, 0.45) !important;
    color: #ffffff !important;
  }
  .stButton > button[kind="primary"]:active {
    box-shadow: 0px 0px 0px 0px !important;
  }

  /* ── Warning badge ── */
  .warn-badge {
    background: #fffbeb;
    border: 2px solid #d97706;
    border-radius: 0px;
    padding: 0.4rem 0.9rem;
    font-size: 0.8rem;
    color: #92400e;
    display: inline-block;
    box-shadow: 2px 2px 0px 0px rgba(217, 119, 6, 0.2);
    font-family: 'Work Sans', sans-serif;
  }

  /* ── Disclosure box (Scenario 2) ── */
  .disclosure-box {
    background: #fffbeb;
    border: 2px solid #d97706;
    border-radius: 0px;
    padding: 1.1rem 1.5rem;
    font-size: 0.85rem;
    color: #78350f;
    line-height: 1.7;
    box-shadow: 4px 4px 0px 0px rgba(217, 119, 6, 0.15);
  }
  .disclosure-box strong { color: #92400e; }

  /* ── Table styling ── */
  [data-testid="stDataFrame"] {
    border-radius: 0px !important;
    border: 2px solid #c9c2b8 !important;
    overflow: hidden;
    box-shadow: 4px 4px 0px 0px rgba(33, 52, 72, 0.12);
  }

  /* ── Expanders ── */
  [data-testid="stExpander"] {
    border: 2px solid #c9c2b8 !important;
    border-radius: 0px !important;
    box-shadow: 3px 3px 0px 0px rgba(33, 52, 72, 0.08);
  }

  /* ── Tabs ── */
  [data-testid="stTabs"] [role="tab"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    border-radius: 0px !important;
  }

  /* ── Dividers ── */
  hr {
    border-top: 2px solid #d4cdc4 !important;
    margin: 1.5rem 0 !important;
  }

  /* ── Download buttons ── */
  [data-testid="stDownloadButton"] > button {
    border-radius: 0px !important;
    border: 2px solid #213448 !important;
    background: #ffffff !important;
    color: #213448 !important;
    box-shadow: 3px 3px 0px 0px rgba(33, 52, 72, 0.15) !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    transition: transform 0.1s, box-shadow 0.1s !important;
  }
  [data-testid="stDownloadButton"] > button:hover {
    transform: translate(-2px, -2px) !important;
    box-shadow: 5px 5px 0px 0px rgba(33, 52, 72, 0.22) !important;
    border-color: #0a7c6e !important;
    color: #0a7c6e !important;
  }
  [data-testid="stDownloadButton"] > button:active {
    transform: translate(2px, 2px) !important;
    box-shadow: 0px 0px 0px !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Numba warmup (runs once per session) ──────────────────────────────────────
@st.cache_resource
def _warmup():
    warmup_numba()
    return True

_warmup()

# ── Data preload (cached for session) ────────────────────────────────────────
@st.cache_resource
def _preload_data():
    load_master_dataset()
    load_research_results()
    return True

with st.spinner("Initializing app..."):
    _preload_data()

# ── Home page content ─────────────────────────────────────────────────────────

# Header
st.markdown("""
<div style="margin-bottom: 0.5rem;">
  <span style="font-size: 2.2rem; font-weight: 800; letter-spacing: -0.03em;">
    ₿ CBBI Strategy Lab
  </span>
</div>
<div style="font-size: 1rem; opacity: 0.55; margin-bottom: 2rem;">
  Bitcoin backtesting simulator powered by CBBI on-chain indicators · Academic research tool
</div>
""", unsafe_allow_html=True)

# ── Navigation cards ──────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown("""
    <div class="nav-card">
      <div class="icon">⚡</div>
      <h3>Strategy Simulator</h3>
      <p>Run custom backtests with any parameters on 14 years of Bitcoin history (2012–2026)</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_Simulator.py", label="Open Simulator →", use_container_width=True)

with col2:
    st.markdown("""
    <div class="nav-card">
      <div class="icon">🔬</div>
      <h3>Research Results</h3>
      <p>Explore Phase 3 optimization outcomes — both academic validation and maximum exploration scenarios</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_Research_Results.py", label="View Research →", use_container_width=True)

with col3:
    st.markdown("""
    <div class="nav-card">
      <div class="icon">📖</div>
      <h3>Documentation</h3>
      <p>Methodology, indicator glossary, metric definitions, and full research disclaimer</p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_Documentation.py", label="Read Docs →", use_container_width=True)

st.divider()

# ── About section ─────────────────────────────────────────────────────────────
col_a, col_b = st.columns([3, 2], gap="large")

with col_a:
    st.markdown("### What is CBBI?")
    st.markdown("""
    The **Crypto Bitcoin Bull/Bear Index (CBBI)** is a composite on-chain indicator that combines
    9 sub-indicators to score the current Bitcoin market cycle on a scale of 0 to 100.
    A score near **0** signals deep accumulation / bear market conditions.
    A score near **100** signals peak euphoria / distribution conditions.

    This app uses the **Trolololo indicator** (Logarithmic Regression / Rainbow Chart) as the
    primary trading signal — identified as the most statistically significant sub-indicator
    through Spearman correlation analysis across 5 lag windows on 2012–2020 data.
    """)

    st.markdown("### How the Simulator Works")
    st.markdown("""
    1. **Set a Buy Threshold** — when Trolololo drops below this, the strategy buys a fixed % of your cash
    2. **Set a Sell Threshold** — when Trolololo rises above this, the strategy sells a fixed % of your BTC
    3. **Between thresholds** — the strategy holds (no action)
    4. Execution happens at the **next day's open price** (T+1) to prevent lookahead bias
    """)

with col_b:
    st.markdown("### Dataset Information")
    df_info = load_master_dataset()
    min_d, max_d = str(df_info.index.min().date()), str(df_info.index.max().date())
    n_rows = len(df_info)

    st.metric("Data Coverage", f"{min_d} → {max_d}")
    st.metric("Total Trading Days", f"{n_rows:,}")
    st.metric("Signal Indicator", "Trolololo (Log Regression)")

    rr = load_research_results()
    st.metric(
        "Optimization Trials Run",
        f"{rr['metadata']['total_trials_per_run']:,} × 2 scenarios",
    )

    st.markdown("""
    <div class="info-strip">
    📌 Data is static — frozen at <b>2026-03-31</b>.<br>
    This app does not fetch live prices.
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer-box">
⚠️ <b>Disclaimer:</b> CBBI Strategy Lab is an academic research tool built for educational purposes.
All results are based on historical backtesting only. Past performance does not guarantee future results.
Nothing on this platform constitutes financial advice. Cryptocurrency trading involves substantial risk of loss.
This tool was developed as part of undergraduate research (PKL 2026) and is not affiliated with CBBI.info or any financial institution.
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; margin-top: 2rem; opacity: 0.3; font-size: 0.78rem;">
  CBBI Strategy Lab · Built on academic research · Data source: cbbi.info + Yahoo Finance
</div>
""", unsafe_allow_html=True)
