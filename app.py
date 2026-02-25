# ======================================================
# INDIAN STOCK DASHBOARD – PRO UI VERSION
# Hybrid Data Engine (TwelveData + yfinance fallback)
# Cleaner Professional Dark Layout
# Structured Visual Hierarchy
# Metric Cards + Fetch Workflow
# ======================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import date
from twelvedata import TDClient

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Indian Stock Dashboard PRO",
    page_icon="📈",
    layout="wide"
)

# ---------------- CUSTOM DARK UI ----------------
st.markdown("""
<style>
    .main {background-color:#0e1117;}
    section[data-testid="stSidebar"] {background-color:#111827;}
    .metric-card {
        background-color:#1f2937;
        padding:20px;
        border-radius:12px;
        text-align:center;
    }
    .section-title {
        font-size:26px;
        font-weight:600;
        margin-top:20px;
        margin-bottom:10px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## 📊 Indian Stock Analysis Dashboard")
st.markdown("Quantitative analysis with structured professional UI.")

# ---------------- API SETUP ----------------
API_KEY = st.secrets.get("TWELVEDATA_API_KEY", None)
td = TDClient(apikey=API_KEY) if API_KEY else None

# ---------------- LOAD COMPANY LIST ----------------
@st.cache_data(ttl=1800)
def load_companies():
    try:
        df = pd.read_csv(
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        )
        df = df[['NAME OF COMPANY', 'SYMBOL']]
        df.columns = ['Company', 'Symbol']
        return df.sort_values("Company")
    except:
        return pd.DataFrame({
            "Company": ["Reliance Industries", "TCS"],
            "Symbol": ["RELIANCE", "TCS"]
        })

companies_df = load_companies()

# ---------------- SIDEBAR ----------------
st.sidebar.markdown("### ⚙️ Stock Controls")

exchange = st.sidebar.radio(
    "Exchange",
    ["NSE", "BSE"],
    horizontal=True
)

company = st.sidebar.selectbox(
    "Search Company",
    companies_df["Company"]
)

symbol = companies_df.loc[
    companies_df["Company"] == company, "Symbol"
].values[0]

start_date = st.sidebar.date_input("Start Date", date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", date.today())

fetch_button = st.sidebar.button("🚀 Fetch Data")

# ---------------- DATA FETCH ----------------
@st.cache_data(ttl=1800)
def fetch_data(symbol, exchange):

    # TwelveData Primary
    if td:
        try:
            ts = td.time_series(
                symbol=symbol,
                exchange=exchange,
                interval="1day",
                outputsize=500
            )
            df = ts.as_pandas()

            if df is not None and not df.empty:
                df = df.sort_index()
                df.rename(columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close"
                }, inplace=True)
                return df, "TwelveData"
        except:
            pass

    # yfinance Fallback
    ticker = symbol + (".NS" if exchange == "NSE" else ".BO")

    df = yf.download(
        ticker,
        start=start_date,
        end=end_date,
        progress=False
    )

    if not df.empty:
        return df, "yfinance"

    return None, None

# ---------------- MAIN WORKFLOW ----------------
if fetch_button:

    data, source = fetch_data(symbol, exchange)

    if data is None:
        st.error("No data available.")
        st.stop()

    st.success(f"Data source: {source}")

    # ----- CALCULATIONS -----
    data["Return"] = data["Close"].pct_change()
    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()

    annual_return = (data["Close"].iloc[-1] /
                     data["Close"].iloc[0]) - 1

    volatility = data["Return"].std() * np.sqrt(252)
    sharpe = annual_return / volatility if volatility else 0

    signal = "BUY" if data["MA20"].iloc[-1] > \
        data["MA50"].iloc[-1] else "SELL"

    # ----- METRIC CARDS -----
    st.markdown('<div class="section-title">📌 Performance Metrics</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Annual Return", f"{annual_return*100:.2f}%")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Volatility", f"{volatility*100:.2f}%")
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Sharpe Ratio", f"{sharpe:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Signal", signal)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ----- IMPROVED CANDLESTICK CHART -----
    st.markdown('<div class="section-title">📈 Price Chart</div>', unsafe_allow_html=True)

    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"]
    )])

    fig.update_layout(
        template="plotly_dark",
        height=600,
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Select stock parameters and click Fetch Data to begin analysis.")
