import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ----- CONFIG (loaded from Streamlit secrets) -----
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Dashboard RaLemby", layout="wide")

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base & font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0f0f0f;
    color: #e0e0e0;
}

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Page padding */
.block-container { padding: 2rem 2.5rem 2rem 2.5rem; }

/* ── Dashboard title ── */
.dash-title {
    font-size: 1.7rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 1.5rem;
    letter-spacing: -0.5px;
}

/* ── Metric card ── */
.metric-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    min-height: 90px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.metric-label {
    font-size: 0.75rem;
    color: #888;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 0.4rem;
}

.metric-value {
    font-size: 1.65rem;
    font-weight: 700;
    line-height: 1.1;
}

.metric-value.positive { color: #4ade80; }
.metric-value.negative { color: #f87171; }
.metric-value.neutral  { color: #ffffff; }

/* ── Section headers ── */
.section-header {
    font-size: 1rem;
    font-weight: 600;
    color: #cccccc;
    margin: 1.8rem 0 0.8rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #2a2a2a;
}

/* ── Dataframe styling ── */
.stDataFrame {
    background: #1a1a1a !important;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #141414;
    border-right: 1px solid #2a2a2a;
}

section[data-testid="stSidebar"] * {
    color: #cccccc !important;
}

/* ── Plotly chart bg ── */
.js-plotly-plot .plotly { background: transparent !important; }

/* ── Caption ── */
.stCaption { color: #555 !important; font-size: 0.72rem; }
</style>
""", unsafe_allow_html=True)

# ── Helper to render a metric card ──────────────────────────────────────────
def metric_card(label: str, value: str, color_class: str = "neutral"):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color_class}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def color_class(val: float) -> str:
    if val > 0: return "positive"
    if val < 0: return "negative"
    return "neutral"

# ── Title ───────────────────────────────────────────────────────────────────
st.markdown('<div class="dash-title">📊 Dashboard RaLemby</div>', unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.header("Settings")
days_filter = st.sidebar.slider("Closed trades history (days)", 7, 365, 30)
if st.sidebar.button("Refresh Now"):
    st.cache_data.clear()

# ── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_data(_days):
    acc = supabase.table("account").select("*").order("timestamp", desc=True).limit(1).execute()
    acc = acc.data[0] if acc.data else {}

    pos = supabase.table("positions").select("*").execute()
    df_positions = pd.DataFrame(pos.data) if pos.data else pd.DataFrame()

    since = (datetime.now() - timedelta(days=_days)).isoformat()
    closed = supabase.table("closed_trades").select("*").filter("close_time", "gte", since).execute()
    df_closed = pd.DataFrame(closed.data) if closed.data else pd.DataFrame()

    return acc, df_positions, df_closed

account, df_positions, df_closed = load_data(days_filter)

# ── Stats ────────────────────────────────────────────────────────────────────
if df_closed.empty:
    stats = {"Total Trades": 0, "Win Rate (%)": 0, "Gross Profit": 0,
             "Gross Loss": 0, "Net P/L": 0, "Profit Factor": 0}
else:
    profits = df_closed["profit"]
    wins    = profits[profits > 0]
    losses  = profits[profits < 0]
    gross_profit = wins.sum()
    gross_loss   = losses.sum()
    net_pl       = gross_profit + gross_loss
    total        = len(profits)
    win_rate     = (len(wins) / total * 100) if total > 0 else 0
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else (float("inf") if gross_profit > 0 else 0)
    stats = {
        "Total Trades":   total,
        "Win Rate (%)":   round(win_rate, 2),
        "Gross Profit":   round(gross_profit, 2),
        "Gross Loss":     round(gross_loss, 2),
        "Net P/L":        round(net_pl, 2),
        "Profit Factor":  round(profit_factor, 2),
    }

balance = account.get("balance", 0)
equity  = account.get("equity", 0)
net_pl  = stats["Net P/L"]
pf      = stats["Profit Factor"]
wr      = stats["Win Rate (%)"]
tt      = stats["Total Trades"]
gp      = stats["Gross Profit"]
gl      = stats["Gross Loss"]

# ── Row 1: 6 metrics ─────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: metric_card("Balance",       f"{balance:,.2f}", "neutral")
with c2: metric_card("Equity",        f"{equity:,.2f}",  "neutral")
with c3: metric_card("Net P/L",       f"{net_pl:+,.2f}", color_class(net_pl))
with c4: metric_card("Profit Factor", f"{pf}",           color_class(pf - 1))
with c5: metric_card("Win Rate",      f"{wr} %",         "neutral")
with c6: metric_card("Total Trades",  f"{tt}",           "neutral")

# ── Row 2: Gross Profit / Loss ───────────────────────────────────────────────
st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
c7, c8, _, _, _, _ = st.columns(6)
with c7: metric_card("Gross Profit", f"+{gp:,.2f}", "positive")
with c8: metric_card("Gross Loss",   f"{gl:,.2f}",  "negative")

# ── Open Positions ───────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📈 Open Positions</div>', unsafe_allow_html=True)
if df_positions.empty:
    st.info("No open positions.")
else:
    cols_to_show = [c for c in ["symbol","type","volume","price_open","sl","tp","profit"] if c in df_positions.columns]
    st.dataframe(df_positions[cols_to_show], use_container_width=True, hide_index=True)

# ── Symbol performance ───────────────────────────────────────────────────────
sym_perf = pd.DataFrame()
if not df_closed.empty:
    sym_perf = df_closed.groupby("symbol").agg(
        Total_Trades=("profit", "count"),
        Win_Rate=("profit", lambda x: round((x > 0).sum() / len(x) * 100, 2)),
        Gross_Profit=("profit", lambda x: round(x[x > 0].sum(), 2)),
        Gross_Loss=("profit", lambda x: round(x[x < 0].sum(), 2)),
        Net_PL=("profit", lambda x: round(x.sum(), 2)),
    ).reset_index()
    sym_perf["Profit_Factor"] = sym_perf.apply(
        lambda r: round(r.Gross_Profit / abs(r.Gross_Loss), 2) if r.Gross_Loss != 0 else (float("inf") if r.Gross_Profit > 0 else 0),
        axis=1
    )

st.markdown('<div class="section-header">📊 Performance by Symbol</div>', unsafe_allow_html=True)
if sym_perf.empty:
    st.info("No closed trades in selected period.")
else:
    st.dataframe(sym_perf, use_container_width=True, hide_index=True)

    fig = px.bar(
        sym_perf, x="symbol", y="Net_PL",
        title="Net P/L by Symbol",
        labels={"Net_PL": "Net Profit / Loss"},
        color="Net_PL",
        color_continuous_scale=["#f87171", "#4ade80"],
        text_auto=".2f"
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#1a1a1a",
        font=dict(color="#cccccc", family="Inter"),
        title_font=dict(size=14, color="#ffffff"),
        coloraxis_showscale=False,
        xaxis=dict(showgrid=False, tickfont=dict(color="#aaa")),
        yaxis=dict(gridcolor="#2a2a2a", tickfont=dict(color="#aaa")),
        margin=dict(t=40, b=20, l=10, r=10),
    )
    fig.update_traces(marker_line_width=0, textfont_color="#ffffff")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Data refreshes every 30 seconds. Use the sidebar to adjust history range.")
