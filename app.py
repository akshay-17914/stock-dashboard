# ======================================================
# NSE STOCK DASHBOARD – PRODUCTION VERSION
# Data Source: Local NSE Universe + yfinance
# ======================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import date
import time
import os

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="NSE Quant Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📊 NSE Quant Stock Dashboard")

# ---------------- LOAD NSE UNIVERSE ----------------
@st.cache_data(ttl=86400)
def load_nse_universe():
    try:
        file_path = os.path.join(os.getcwd(), "nse_universe.csv")
        df = pd.read_csv(file_path)
        df = df.dropna()
        return df.sort_values("Company")
    except Exception as e:
        st.error("NSE universe file missing. Run update script first.")
        return pd.DataFrame({
            "Company": ["Reliance Industries"],
            "Symbol": ["RELIANCE"]
        })

companies_df = load_nse_universe()

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

auto_refresh = st.sidebar.slider("Auto Refresh (seconds)", 0, 300, 0)

fetch_button = st.sidebar.button("🚀 Fetch Data")

# ---------------- FETCH DATA ----------------
@st.cache_data(ttl=60)
def fetch_data(symbol, start, end):

    ticker = symbol + ".NS"

    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            progress=False
        )

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Close']].dropna()

        return df

    except:
        return None

# ---------------- MAIN WORKFLOW ----------------
if fetch_button:

    data = fetch_data(symbol, start_date, end_date)

    if data is None:
        st.error("No price data available.")
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

    # ---------------- METRICS DISPLAY ----------------
    st.subheader("📈 Quant Stock Ratings")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Annual Return", f"{annual_return*100:.2f}%")
    col2.metric("Volatility", f"{volatility*100:.2f}%")
    col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col4.metric("Signal", signal)

    st.write("### Rating:", rating)

    # ---------------- CHART ----------------
    st.subheader("Price Chart")

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

# ---------------- AUTO REFRESH ----------------
if auto_refresh > 0:
    time.sleep(auto_refresh)
    st.rerun()

