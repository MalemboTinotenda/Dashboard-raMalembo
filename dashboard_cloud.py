import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ----- CONFIG (loaded from Streamlit secrets) -----# Use string lookups, not the direct URLs
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Now initialize your client using those variables
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

#SUPABASE_URL = st.secrets["https://efvzdizdtvqigkxornss.supabase.co/rest/v1/"]
#SUPABASE_KEY = st.secrets["yJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmdnpkaXpkdHZxaWdreG9ybnNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA1NzMyMzEsImV4cCI6MjA5NjE0OTIzMX0.AsNuGTnpM-26M15jXkSxI4oSGwPWurqHtQDfMmWOWfg"]

#supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="MT5 Dashboard", layout="wide")
st.title("📊 MT5 Trading Dashboard (Cloud)")

# Date filter for closed trades
st.sidebar.header("Settings")
days_filter = st.sidebar.slider("Closed trades history (days)", 7, 365, 30)

if st.sidebar.button("Refresh Now"):
    st.cache_data.clear()

# Data loading (cached for 30 seconds)
@st.cache_data(ttl=30)
def load_data(_days):
    # Account (latest entry)
    acc = supabase.table("account").select("*").order("timestamp", desc=True).limit(1).execute()
    if acc.data:
        acc = acc.data[0]
    else:
        acc = {}

    # Open positions
    pos = supabase.table("positions").select("*").execute()
    df_positions = pd.DataFrame(pos.data) if pos.data else pd.DataFrame()

    # Closed trades within date range
    since = (datetime.now() - timedelta(days=_days)).isoformat()
    closed = supabase.table("closed_trades").select("*").filter("close_time", "gte", since).execute()
    df_closed = pd.DataFrame(closed.data) if closed.data else pd.DataFrame()

    return acc, df_positions, df_closed

account, df_positions, df_closed = load_data(days_filter)

# Compute stats
if df_closed.empty:
    stats = {"Total Trades": 0, "Win Rate (%)": 0, "Gross Profit": 0, "Gross Loss": 0, "Net P/L": 0, "Profit Factor": 0}
else:
    profits = df_closed["profit"]
    wins = profits[profits > 0]
    losses = profits[profits < 0]
    gross_profit = wins.sum()
    gross_loss = losses.sum()
    net_pl = gross_profit + gross_loss
    total = len(profits)
    win_rate = (len(wins) / total * 100) if total > 0 else 0
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else float("inf") if gross_profit > 0 else 0
    stats = {
        "Total Trades": total,
        "Win Rate (%)": round(win_rate, 2),
        "Gross Profit": round(gross_profit, 2),
        "Gross Loss": round(gross_loss, 2),
        "Net P/L": round(net_pl, 2),
        "Profit Factor": round(profit_factor, 2)
    }

# Symbol performance
sym_perf = pd.DataFrame()
if not df_closed.empty:
    sym_perf = df_closed.groupby("symbol").agg(
        Total_Trades=("profit", "count"),
        Win_Rate=("profit", lambda x: (x > 0).sum() / len(x) * 100),
        Gross_Profit=("profit", lambda x: x[x > 0].sum()),
        Gross_Loss=("profit", lambda x: x[x < 0].sum()),
        Net_PL=("profit", "sum")
    ).reset_index()
    sym_perf["Profit_Factor"] = sym_perf.apply(
        lambda row: round(row.Gross_Profit / abs(row.Gross_Loss), 2) if row.Gross_Loss != 0 else float("inf") if row.Gross_Profit > 0 else 0,
        axis=1
    )
    sym_perf = sym_perf.round(2)

# --- UI ---
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Balance", f"{account.get('balance', 0):,.2f}")
with col2:
    st.metric("Equity", f"{account.get('equity', 0):,.2f}")
with col3:
    st.metric("Net P/L", f"{stats['Net P/L']:,.2f}")
with col4:
    st.metric("Profit Factor", f"{stats['Profit Factor']}")
with col5:
    st.metric("Win Rate", f"{stats['Win Rate (%)']} %")
with col6:
    st.metric("Total Trades", stats["Total Trades"])

col7, col8 = st.columns(2)
with col7:
    st.metric("Gross Profit", f"{stats['Gross Profit']:,.2f}")
with col8:
    st.metric("Gross Loss", f"{stats['Gross Loss']:,.2f}")

st.subheader("📈 Open Positions")
if df_positions.empty:
    st.info("No open positions.")
else:
    st.dataframe(df_positions[["symbol", "type", "volume", "price_open", "sl", "tp", "profit"]], use_container_width=True, hide_index=True)

st.subheader("📊 Performance by Symbol")
if sym_perf.empty:
    st.info("No closed trades in selected period.")
else:
    st.dataframe(sym_perf, use_container_width=True, hide_index=True)
    fig = px.bar(sym_perf, x="symbol", y="Net_PL", title="Net P/L by Symbol",
                 labels={"Net_PL": "Net Profit/Loss"}, color="Net_PL",
                 color_continuous_scale=["red", "green"], text_auto=".2f")
    st.plotly_chart(fig, use_container_width=True)

st.caption("Data refreshes every 30 seconds. Use the sidebar to change the history range.")
