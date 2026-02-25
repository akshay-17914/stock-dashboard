import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date
import time

# ==========================
# PAGE CONFIG
# ==========================
st.set_page_config(
    page_title="Indian Stock Dashboard",
    page_icon="📈",
    layout="wide"
)

# ==========================
# CUSTOM CSS (UI IMPROVEMENT)
# ==========================
st.markdown("""
<style>
    .main {background-color:#0e1117;}
    .stMetric {background:#161a23;padding:15px;border-radius:10px}
    .title {font-size:40px;font-weight:700}
</style>
""", unsafe_allow_html=True)

# ==========================
# TITLE
# ==========================
st.markdown('<p class="title">📊 Indian Stock Analysis Dashboard</p>', unsafe_allow_html=True)

# ==========================
# SIDEBAR SETTINGS
# ==========================
st.sidebar.title("⚙️ Stock Settings")

exchange = st.sidebar.radio("Exchange", ["NSE", "BSE"], horizontal=True)

stocks = {
    "Reliance Industries": "RELIANCE",
    "TCS": "TCS",
    "Infosys": "INFY",
    "HDFC Bank": "HDFCBANK",
    "ICICI Bank": "ICICIBANK",
    "NTPC": "NTPC",
    "Tata Steel": "TATASTEEL"
}

company = st.sidebar.selectbox("Search Company", list(stocks.keys()))
symbol = stocks[company] + (".NS" if exchange == "NSE" else ".BO")

start_date = st.sidebar.date_input("Start Date", date(2023,1,1))
end_date = st.sidebar.date_input("End Date", date.today())

fetch = st.sidebar.button("Fetch Data")

# ==========================
# DATA FETCH
# ==========================
@st.cache_data(ttl=1800)
def get_data(sym, start, end):
    df = yf.download(sym, start=start, end=end, progress=False)
    return df

if fetch:
    data = get_data(symbol, start_date, end_date)

    if data.empty:
        st.error("No data available.")
        st.stop()

    data["Return"] = data["Close"].pct_change()
    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()

    annual_return = (data["Close"].iloc[-1] / data["Close"].iloc[0]) - 1
    volatility = data["Return"].std() * np.sqrt(252)
    sharpe = annual_return / volatility if volatility != 0 else 0

    signal = "BUY" if data["MA20"].iloc[-1] > data["MA50"].iloc[-1] else "SELL"

    # SCORE
    score = 0
    if annual_return > 0: score += 1
    if volatility < 0.4: score += 1
    if sharpe > 1: score += 1
    if signal == "BUY": score += 1

    rating = "Strong Buy" if score >= 3 else "Watchlist" if score == 2 else "Avoid"

    # ==========================
    # METRICS ROW
    # ==========================
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Annual Return", f"{annual_return*100:.2f}%")
    col2.metric("Volatility", f"{volatility*100:.2f}%")
    col3.metric("Sharpe Ratio", f"{sharpe:.2f}")
    col4.metric("Signal", signal)

    st.markdown("---")

    # ==========================
    # PRICE CHART
    # ==========================
    st.subheader(f"📈 {symbol} Price Chart")
    st.line_chart(data[["Close","MA20","MA50"]].dropna())

    st.success(f"Rating: {rating} | Score: {score}")

else:
    st.info("Select stock and click Fetch Data.")



