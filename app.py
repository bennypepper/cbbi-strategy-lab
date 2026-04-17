"""
app.py
======
CBBI Strategy Lab — Streamlit entry point and home page.

Responsibilities:
  1. Page config + global CSS (via core.styles)
  2. SVG favicon injection
  3. Numba JIT warmup on startup
  4. Home page content (hero, nav cards with SVG icons, about, metrics, disclaimer)
"""

import streamlit as st

from core.data_loader import load_master_dataset, load_research_results, fetch_cbbi_live
from core.engine import warmup_numba
from core.styles import inject_css, ICON_ZAP, ICON_CHART_BARS, ICON_BOOK
from core.utils import format_percentage, format_currency

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

# ── fix #18: SVG favicon (teal ₿, avoids cross-platform emoji inconsistency) ──
st.markdown(
    "<link rel='shortcut icon' href=\"data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
    "<text y='.9em' font-size='90' fill='%230a7c6e'>&#8383;</text>"
    "</svg>\"/>",
    unsafe_allow_html=True,
)

# ── Global design-system CSS (shared across all pages) ───────────────────────
inject_css()

# ── Numba warmup + data preload (cached for session) ─────────────────────────
@st.cache_resource
def _warmup():
    warmup_numba()
    return True


@st.cache_resource
def _preload_data():
    load_master_dataset()
    load_research_results()
    try:
        fetch_cbbi_live()
    except Exception:
        pass
    return True


with st.spinner("Initializing…"):
    _warmup()
    _preload_data()

# ── Home page: Header ─────────────────────────────────────────────────────────
# fix #10: subtitle uses explicit color + weight (not just opacity)
# fix #13: hero tagline gives first-visit context before the cards
st.markdown(
    """
    <div style="margin-bottom:0.15rem;">
      <span class="page-title">&#8383; CBBI Strategy Lab</span>
    </div>
    <p class="page-subtitle">
      Bitcoin backtesting simulator powered by CBBI on-chain indicators &middot; Academic research tool
    </p>
    <div class="hero-tagline">
      Test, validate, and explore Bitcoin timing strategies &mdash;
      1.29&thinsp;M optimization trials, 14 years of on-chain data, zero lookahead bias.
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Dynamic Stats Cards ───────────────────────────────────────────────────────
df_hist = load_master_dataset()
try:
    df_live = fetch_cbbi_live()
    latest_date = df_live.index.max()
    latest_row = df_live.loc[latest_date]
    is_live = True
except Exception:
    df_live = df_hist
    latest_date = df_hist.index.max()
    latest_row = df_hist.loc[latest_date]
    is_live = False

latest_cbbi = float(latest_row['trolololo'])
latest_price = float(latest_row['btc_open'])
total_days = len(df_live)
min_date = str(df_live.index.min().date())

# Determine zone and colors
zone_label = "EXTREME OVERVALUED"
zone_color = "#d93025"  # Red
if latest_cbbi < 15:
    zone_label, zone_color = "EXTREME UNDERVALUED", "#1a73e8" # Blue
elif latest_cbbi < 35:
    zone_label, zone_color = "UNDERVALUED", "#188038" # Green
elif latest_cbbi < 65:
    zone_label, zone_color = "NEUTRAL", "#e37400" # Yellow/Orange
elif latest_cbbi < 85:
    zone_label, zone_color = "OVERVALUED", "#d93025" # Orange (red-orange)

st.markdown(
    f"""
    <div style="display:flex; flex-wrap:wrap; gap:1.25rem; margin-top:1.5rem; margin-bottom:2.5rem;">
      <!-- Card 1: Trolololo Index -->
      <div style="flex:1; min-width:250px; background:#ffffff; border-radius:0; padding:1.5rem; border:2px solid #c9c2b8; box-shadow:5px 5px 0px 0px rgba(33,52,72,0.15);">
        <div style="font-family:'Inter', sans-serif; font-size:0.75rem; font-weight:700; color:#547792; letter-spacing:0.08em; margin-bottom:0.5rem; text-transform:uppercase;">Trolololo Index</div>
        <div style="font-family:'Space Grotesk', sans-serif; font-size:2.8rem; font-weight:800; color:#213448; line-height:1; margin-bottom:0.75rem; letter-spacing:-0.03em;">{format_percentage(latest_cbbi)}</div>
        <div style="display:inline-block; font-family:'Inter', sans-serif; background:{zone_color}12; color:{zone_color}; padding:0.25rem 0.75rem; font-size:0.75rem; font-weight:700; margin-bottom:1.5rem; text-transform:uppercase; border:2px solid {zone_color}; box-shadow:2px 2px 0px 0px {zone_color}40;">
          {zone_label}
        </div>
        <div style="height:6px; width:100%; background:linear-gradient(90deg, #1a73e8 0%, #188038 25%, #e37400 50%, #d93025 75%, #a50e0e 100%); border:1px solid #c9c2b8; position:relative;">
            <div style="position:absolute; left:{min(latest_cbbi, 100)}%; top:-5px; height:14px; width:4px; background:#ffffff; border:1px solid #213448; box-shadow:1px 1px 0px #213448; margin-left:-2px;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; font-family:'Inter', sans-serif; font-size:0.65rem; font-weight:600; color:#547792; margin-top:0.6rem;">
           <span>0%</span><span>50%</span><span>100%</span>
        </div>
      </div>

      <!-- Card 2: BTC Price -->
      <div style="flex:1; min-width:250px; background:#ffffff; border-radius:0; padding:1.5rem; border:2px solid #c9c2b8; box-shadow:5px 5px 0px 0px rgba(33,52,72,0.15); display:flex; flex-direction:column; justify-content:center;">
        <div style="font-family:'Inter', sans-serif; font-size:0.75rem; font-weight:700; color:#547792; letter-spacing:0.08em; margin-bottom:0.5rem; text-transform:uppercase;">BTC Price</div>
        <div style="font-family:'Space Grotesk', sans-serif; font-size:2.8rem; font-weight:800; color:#0a7c6e; line-height:1; margin-bottom:0.5rem; letter-spacing:-0.03em;">{format_currency(latest_price)}</div>
        <div style="font-family:'Work Sans', sans-serif; font-size:0.95rem; color:#547792; font-weight:500;">Current market price</div>
      </div>

      <!-- Card 3: Data Points -->
      <div style="flex:1; min-width:250px; background:#ffffff; border-radius:0; padding:1.5rem; border:2px solid #c9c2b8; box-shadow:5px 5px 0px 0px rgba(33,52,72,0.15); display:flex; flex-direction:column; justify-content:center;">
        <div style="font-family:'Inter', sans-serif; font-size:0.75rem; font-weight:700; color:#547792; letter-spacing:0.08em; margin-bottom:0.5rem; text-transform:uppercase;">Data Points</div>
        <div style="font-family:'Space Grotesk', sans-serif; font-size:2.8rem; font-weight:800; color:#d97706; line-height:1; margin-bottom:0.5rem; letter-spacing:-0.03em;">{total_days:,}</div>
        <div style="font-family:'Work Sans', sans-serif; font-size:0.95rem; color:#547792; font-weight:500;">Since {min_date}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── fix #1 #4 #5 #14: Nav cards with SVG icons + CTA inside the card ─────────
# Cards use pure-HTML <a> for self-contained, equal-height layout.
# CTA (.nav-card-cta) is pinned to the bottom via flex layout.
col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown(
        f"""
        <a href="/Simulator" target="_self" class="nav-card-link">
          <div class="nav-card">
            <div class="nav-card-icon">{ICON_ZAP}</div>
            <h3>Strategy Simulator</h3>
            <p>Run custom backtests with any parameters on 14 years of
               Bitcoin history (2012&ndash;2026)</p>
            <div class="nav-card-cta">Open Simulator &rarr;</div>
          </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        f"""
        <a href="/Research_Results" target="_self" class="nav-card-link">
          <div class="nav-card">
            <div class="nav-card-icon">{ICON_CHART_BARS}</div>
            <h3>Research Results</h3>
            <p>Explore Phase&nbsp;3 optimization outcomes &mdash; both academic
               validation and maximum exploration scenarios</p>
            <div class="nav-card-cta">View Research &rarr;</div>
          </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        f"""
        <a href="/Documentation" target="_self" class="nav-card-link">
          <div class="nav-card">
            <div class="nav-card-icon">{ICON_BOOK}</div>
            <h3>Documentation</h3>
            <p>Methodology, indicator glossary, metric definitions, and full
               research disclaimer</p>
            <div class="nav-card-cta">Read Docs &rarr;</div>
          </div>
        </a>
        """,
        unsafe_allow_html=True,
    )

# fix #12: divider now has margin: 2.5rem via global CSS
st.divider()

# ── About section ─────────────────────────────────────────────────────────────
# fix #7: balanced 1:1 columns (was 3:2, causing density mismatch)
col_a, col_b = st.columns([1, 1], gap="large")

with col_a:
    st.markdown("### What is CBBI?")
    # fix #9: max-width: 65ch on paragraph text to control line length
    st.markdown(
        """
        <p style="max-width:65ch;line-height:1.68;color:#2d3f50;font-size:0.95rem;margin-bottom:0.85rem;">
          The <strong>Crypto Bitcoin Bull/Bear Index (CBBI)</strong> is a composite on-chain indicator
          that combines 9 sub-indicators to score the current Bitcoin market cycle on a scale of 0&nbsp;to&nbsp;100.
          A score near <strong>0</strong> signals deep accumulation&nbsp;/ bear market conditions.
          A score near <strong>100</strong> signals peak euphoria&nbsp;/ distribution conditions.
        </p>
        <p style="max-width:65ch;line-height:1.68;color:#2d3f50;font-size:0.95rem;">
          This app uses the <strong>Trolololo indicator</strong> (Logarithmic Regression&nbsp;/ Rainbow Chart)
          as the primary trading signal &mdash; identified as the most statistically significant
          sub-indicator through Spearman correlation analysis across 5 lag windows on 2012&ndash;2020 data.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### How the Simulator Works")
    st.markdown(
        """
        <ol style="max-width:65ch;line-height:1.75;color:#2d3f50;font-size:0.95rem;padding-left:1.3rem;">
          <li><strong>Set a Buy Threshold</strong> &mdash; when Trolololo drops below this,
              the strategy buys a fixed&nbsp;% of your cash</li>
          <li><strong>Set a Sell Threshold</strong> &mdash; when Trolololo rises above this,
              the strategy sells a fixed&nbsp;% of your BTC</li>
          <li><strong>Between thresholds</strong> &mdash; the strategy holds (no action)</li>
          <li>Execution happens at the <strong>next day&rsquo;s open price</strong> (T+1)
              to prevent lookahead bias</li>
        </ol>
        """,
        unsafe_allow_html=True,
    )

with col_b:
    st.markdown("### Dataset Information")

    # fix #15: spinner communicates data-load latency on first visit
    # fix #15: spinner communicates data-load latency
    min_d = str(df_live.index.min().date())
    max_d = str(df_live.index.max().date())
    n_rows = len(df_live)

    # fix #2 & #6: clamp font-size + word-break in global CSS prevents truncation
    st.metric("Data Coverage", f"{min_d} → {max_d}")
    st.metric("Total Trading Days", f"{n_rows:,}")
    st.metric("Signal Indicator", "Trolololo (Log Regression)")

    rr = load_research_results()
    st.metric(
        "Optimization Trials Run",
        f"{rr['metadata']['total_trials_per_run']:,} × 2 scenarios",
    )

    if is_live:
        st.markdown(
            f"""
            <div class="info-strip" style="background:#edf4f7; border-left:4px solid #0a7c6e; padding:1rem; border-radius:0; color:#213448; font-family:'Work Sans', sans-serif;">
            <span style="color:#0a7c6e;font-weight:700;">&#128308; Live API Connected</span> &mdash; Using latest data up to <b>{max_d}</b>.<br>
            App fetches daily updates directly from colintalkscrypto.com endpoints.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="info-strip" style="background:#fffbeb; border-left:4px solid #d97706; padding:1rem; border-radius:0; color:#78350f; font-family:'Work Sans', sans-serif;">
            <span style="color:#d97706;font-weight:700;">&#9888;&#65039; Offline Mode</span> &mdash; Live data fetch failed. Displaying static data frozen at <b>{max_d}</b>.
            </div>
            """,
            unsafe_allow_html=True,
        )

st.divider()

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="disclaimer-box">
    &#9888;&#65039; <b>Disclaimer:</b> CBBI Strategy Lab is an academic research tool built for educational purposes.
    All results are based on historical backtesting only. Past performance does not guarantee future results.
    Nothing on this platform constitutes financial advice. Cryptocurrency trading involves substantial risk of loss.
    This tool was developed as part of undergraduate research (PKL 2026) and is not affiliated with CBBI.info
    or any financial institution.
    </div>
    """,
    unsafe_allow_html=True,
)

# ── fix #17: Footer opacity increased from 0.3 → 0.55 ───────────────────────
st.markdown(
    """
    <div style="text-align:center;margin-top:2.5rem;opacity:0.55;font-size:0.78rem;
                color:#547792;font-family:'Inter',sans-serif;">
      CBBI Strategy Lab &middot; Built on academic research &middot;
      Data source: cbbi.info + Yahoo Finance
    </div>
    """,
    unsafe_allow_html=True,
)
