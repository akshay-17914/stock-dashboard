# ======================================================
# NSE QUANT DASHBOARD – DATABASE VERSION
# Reads from local price_db (NO live API calls)
# ======================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date
import os

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="NSE Quant Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📊 NSE Quant Stock Dashboard (Database Mode)")

# ---------------- LOAD NSE UNIVERSE ----------------
@st.cache_data(ttl=86400)
def load_universe():
    try:
        df = pd.read_csv("nse_universe.csv")
        return df.sort_values("Company")
    except:
        st.error("Run update_nse_universe.py first.")
        return pd.DataFrame()

companies_df = load_universe()

if companies_df.empty:
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.header("🔎 Stock Settings")

company = st.sidebar.selectbox(
    "Search NSE Company",
    companies_df["Company"]
)

symbol = companies_df.loc[
    companies_df["Company"] == company,
    "Symbol"
].values[0]

start_date = st.sidebar.date_input("Start Date", date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", date.today())

# ---------------- LOAD PRICE DATA FROM DATABASE ----------------
@st.cache_data(ttl=60)
def load_price_data(symbol):

    file_path = f"price_db/{symbol}.csv"

    if not os.path.exists(file_path):
        return None

    df = pd.read_csv(file_path, index_col=0, parse_dates=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if "Close" not in df.columns:
        return None

    return df

data = load_price_data(symbol)

if data is None:
    st.error("No local price data found. Run update_prices.py first.")
    st.stop()

# Filter date range
data = data[(data.index >= pd.to_datetime(start_date)) &
            (data.index <= pd.to_datetime(end_date))]

if len(data) < 50:
    st.warning("Not enough historical data for analysis.")
    st.stop()

# ---------------- QUANT CALCULATIONS ----------------
data["Return"] = data["Close"].pct_change()
data["MA20"] = data["Close"].rolling(20).mean()
data["MA50"] = data["Close"].rolling(50).mean()

annual_return = (data["Close"].iloc[-1] /
                 data["Close"].iloc[0]) - 1

volatility = data["Return"].std() * np.sqrt(252)
sharpe = annual_return / volatility if volatility != 0 else 0

signal = "BUY" if data["MA20"].iloc[-1] > \
    data["MA50"].iloc[-1] else "SELL"

# ---------------- SCORING ----------------
score = 0
if annual_return > 0:
    score += 1
if volatility < 0.4:
    score += 1
if sharpe > 1:
    score += 1
if signal == "BUY":
    score += 1

rating = (
    "Strong Buy" if score >= 3
    else "Watchlist" if score == 2
    else "Avoid"
)

# ---------------- METRICS ----------------
st.subheader("📈 Quant Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Annual Return", f"{annual_return*100:.2f}%")
col2.metric("Volatility", f"{volatility*100:.2f}%")
col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
col4.metric("Signal", signal)

st.write("### Rating:", rating)

# ---------------- CHART ----------------
st.subheader("📊 Price Chart")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=data.index,
    y=data["Close"],
    name="Close"
))

fig.add_trace(go.Scatter(
    x=data.index,
    y=data["MA20"],
    name="MA20"
))

fig.add_trace(go.Scatter(
    x=data.index,
    y=data["MA50"],
    name="MA50"
))

fig.update_layout(
    template="plotly_dark",
    height=600,
    xaxis_title="Date",
    yaxis_title="Price"
)

st.plotly_chart(fig, use_container_width=True)
