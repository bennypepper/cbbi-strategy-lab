"""
core/styles.py
==============
Centralized CSS for CBBI Strategy Lab.
Import and call inject_css() on every Streamlit page for consistent styling
across the entire app (sidebar active state, metric cards, buttons, etc.).
"""

import streamlit as st

# ── SVG icon library (Lucide-style, stroke-based) ─────────────────────────────
ICON_ZAP = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>"""
ICON_CHART_BARS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>"""
ICON_BOOK = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>"""

# ── Global CSS design system ───────────────────────────────────────────────────
_GLOBAL_CSS = """
<style>
  /* ── Google Fonts ── */
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Work+Sans:wght@300;400;500;600&family=Inter:wght@400;500;600&display=swap');

  /* ── Base reset ── */
  html, body, [class*="css"] {
    font-family: 'Work Sans', sans-serif;
    letter-spacing: -0.01em;
  }
  .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 100%; }

  /* ── Typography hierarchy ── */
  h1, h2, h3, h4 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.03em !important;
    font-weight: 700 !important;
    color: #213448 !important;
  }

  /* ── Page header elements ── */
  .page-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(1.8rem, 3.5vw, 2.5rem);
    font-weight: 800;
    letter-spacing: -0.04em;
    color: #213448;
    margin: 0 0 0.2rem 0;
    line-height: 1.08;
  }
  .page-subtitle {
    font-family: 'Work Sans', sans-serif;
    font-size: 0.92rem;
    color: #547792;
    font-weight: 500;
    margin: 0 0 0.4rem 0;
    line-height: 1.4;
  }

  /* ── Hero tagline ── */
  .hero-tagline {
    font-family: 'Work Sans', sans-serif;
    font-size: 1rem;
    color: #0a7c6e;
    font-weight: 600;
    letter-spacing: -0.005em;
    margin: 0.3rem 0 1.8rem 0;
    line-height: 1.5;
    border-left: 3px solid #0a7c6e;
    padding-left: 0.85rem;
    max-width: 700px;
  }

  /* ── Metric cards ── */
  [data-testid="metric-container"],
  .metric-card {
    background: #ffffff;
    border: 2px solid #d4cdc4;
    border-radius: 0px !important;
    padding: 1.1rem 1.2rem;
    box-shadow: 4px 4px 0px 0px rgba(33, 52, 72, 0.18);
    transition: box-shadow 0.15s, transform 0.15s;
    overflow: hidden;
  }
  [data-testid="metric-container"]:hover,
  .metric-card:hover {
    box-shadow: 6px 6px 0px 0px rgba(33, 52, 72, 0.28);
    transform: translate(-1px, -1px);
  }
  [data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.68rem !important;
    color: #547792 !important;
    opacity: 1 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    font-weight: 600 !important;
  }
  /* fix #2 & #6 — responsive font + word-wrap so values never clip */
  [data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: clamp(0.9rem, 1.8vw, 1.5rem) !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.25 !important;
    color: #213448 !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    white-space: normal !important;
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: #ede8e0;
    border-right: 2px solid #c9c2b8;
  }

  /* ── Sidebar nav: active state + hover (fix #3 & #8) ── */
  [data-testid="stSidebarNavLink"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    color: #213448 !important;
    border-left: 3px solid transparent !important;
    border-radius: 0px !important;
    padding: 0.45rem 1rem 0.45rem 0.85rem !important;
    margin: 0.1rem 0 !important;
    transition: color 0.15s, background 0.15s, border-color 0.15s !important;
    text-decoration: none !important;
  }
  [data-testid="stSidebarNavLink"]:hover {
    color: #0a7c6e !important;
    background: rgba(10, 124, 110, 0.05) !important;
    border-left-color: rgba(10, 124, 110, 0.3) !important;
  }
  /* fix #3 — active page highlight */
  [data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(10, 124, 110, 0.09) !important;
    color: #0a7c6e !important;
    font-weight: 700 !important;
    border-left-color: #0a7c6e !important;
  }

  /* fix #8 — rename "app" → "Home" via CSS content trick */
  [data-testid="stSidebarNavLink"][href="/"] p,
  [data-testid="stSidebarNav"] a[href="/"] p {
    visibility: hidden;
    position: relative;
  }
  [data-testid="stSidebarNavLink"][href="/"] p::before,
  [data-testid="stSidebarNav"] a[href="/"] p::before {
    content: "Home";
    visibility: visible;
    position: absolute;
    left: 0;
    top: 0;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: inherit;
    color: inherit;
  }

  /* ── Nav cards (fix #1 SVG, #4 equal heights, #5 CTA inside) ── */
  a.nav-card-link {
    display: block;
    text-decoration: none !important;
    color: inherit;
  }
  .nav-card {
    background: #ffffff;
    border: 2px solid #c9c2b8;
    border-radius: 0;
    padding: 1.8rem 1.8rem 1.4rem;
    min-height: 280px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 0.65rem;
    box-shadow: 5px 5px 0px 0px rgba(33, 52, 72, 0.15);
    transition: box-shadow 0.15s, transform 0.15s, border-color 0.15s;
    box-sizing: border-box;
  }
  a.nav-card-link:hover .nav-card {
    border-color: #0a7c6e;
    box-shadow: 7px 7px 0px 0px rgba(10, 124, 110, 0.22);
    transform: translate(-2px, -2px);
  }
  a.nav-card-link:hover .nav-card-cta {
    background: #0a7c6e;
    color: #ffffff;
    border-color: #0a7c6e;
    box-shadow: 2px 2px 0px 0px rgba(10, 124, 110, 0.3);
  }
  /* fix #1 — SVG icon box (replaces emojis) */
  .nav-card-icon {
    width: 52px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f2ede6;
    border: 2px solid #d4cdc4;
    flex-shrink: 0;
    margin-bottom: 0.2rem;
  }
  .nav-card-icon svg {
    width: 24px;
    height: 24px;
    stroke: #213448;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
    fill: none;
  }
  .nav-card h3 {
    margin: 0;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.08rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #213448;
    flex-shrink: 0;
  }
  /* fix #11 — card description contrast darkened */
  .nav-card p {
    margin: 0;
    font-size: 0.84rem;
    color: #3d5a6e;
    line-height: 1.55;
    font-family: 'Work Sans', sans-serif;
    flex-grow: 1;
  }
  /* fix #5 & #14 — proper button CTA pinned to card bottom */
  .nav-card-cta {
    margin-top: auto;
    width: 100%;
    padding: 0.52rem 0.8rem;
    background: #ffffff;
    border: 2px solid #213448;
    color: #213448;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: -0.01em;
    box-shadow: 3px 3px 0px 0px rgba(33, 52, 72, 0.14);
    transition: background 0.15s, color 0.15s, border-color 0.15s, box-shadow 0.15s;
    flex-shrink: 0;
    text-align: center;
  }

  /* ── Disclaimer box ── */
  .disclaimer-box {
    background: #fff5f5;
    border: 2px solid rgba(220, 60, 60, 0.35);
    border-radius: 0;
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
    border-radius: 0;
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
    margin-bottom: 0.4rem;
  }

  /* ── Buttons: Tactile Neo-Brutalism ── */
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
    border-radius: 0;
    padding: 0.4rem 0.9rem;
    font-size: 0.8rem;
    color: #92400e;
    display: inline-block;
    box-shadow: 2px 2px 0px 0px rgba(217, 119, 6, 0.2);
    font-family: 'Work Sans', sans-serif;
  }

  /* ── Disclosure box ── */
  .disclosure-box {
    background: #fffbeb;
    border: 2px solid #d97706;
    border-radius: 0;
    padding: 1.1rem 1.5rem;
    font-size: 0.85rem;
    color: #78350f;
    line-height: 1.7;
    box-shadow: 4px 4px 0px 0px rgba(217, 119, 6, 0.15);
  }
  .disclosure-box strong { color: #92400e; }

  /* ── Table ── */
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

  /* fix #12 — dividers with more breathing room */
  hr {
    border-top: 2px solid #d4cdc4 !important;
    margin: 2.5rem 0 !important;
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

  .metric-label {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.68rem !important;
    color: #547792 !important;
    opacity: 1 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    font-weight: 600 !important;
    margin-bottom: 0.35rem;
  }
  .metric-value {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: clamp(0.9rem, 1.8vw, 1.5rem) !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em !important;
    line-height: 1.25 !important;
    color: #0a7c6e !important;
    word-break: break-word !important;
    overflow-wrap: break-word !important;
    white-space: normal !important;
    margin-bottom: 0.25rem;
  }
  .metric-subtext {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.75rem !important;
    color: #64748b !important;
    font-weight: 500 !important;
    line-height: 1.4 !important;
  }
</style>
"""


def inject_css() -> None:
    """Inject the global design system CSS into the current Streamlit page.

    Call this once per page, immediately after st.set_page_config().
    """
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<div style='text-align: center; color: #64748b; font-size: 0.8rem; line-height: 1.5;'>"
        "Built with ☕ by <br>"
        "<a href='https://github.com/bennypepper' target='_blank' style='color: #0a7c6e; font-weight: 600; text-decoration: none;'>Benedict Pepper</a><br>"
        "Ma Chung University<br>"
        "PKL Research © 2026"
        "</div>", 
        unsafe_allow_html=True
    )
