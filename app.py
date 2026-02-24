# ======================================================
# INDIAN STOCK DASHBOARD (HYBRID DATA ENGINE)
# Primary: TwelveData
# Fallback: yfinance
# ======================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import time
from datetime import date
from twelvedata import TDClient

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(page_title="Indian Stock Dashboard", layout="wide")
st.title("📊 Indian Stock Analysis Dashboard")

# ===============================
# API KEY (SAFE)
# ===============================
API_KEY = st.secrets.get("TWELVEDATA_API_KEY", None)

td = None
if API_KEY:
    td = TDClient(apikey=API_KEY)

# ===============================
# LOAD NSE COMPANY LIST
# ===============================
@st.cache_data(ttl=1800)
def load_companies():
    try:
        nse = pd.read_csv(
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        )
        nse = nse[['NAME OF COMPANY', 'SYMBOL']]
        nse.rename(columns={
            "NAME OF COMPANY": "Company",
            "SYMBOL": "Symbol"
        }, inplace=True)
        return nse.sort_values("Company")
    except:
        return pd.DataFrame({
            "Company": ["Reliance Industries", "TCS"],
            "Symbol": ["RELIANCE", "TCS"]
        })

companies_df = load_companies()

# ===============================
# SIDEBAR
# ===============================
st.sidebar.header("🔎 Stock Settings")

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
    companies_df["Company"] == company,
    "Symbol"
].values[0]

start_date = st.sidebar.date_input("Start Date", date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", date.today())

fetch_button = st.sidebar.button("Fetch Data")

# ===============================
# HYBRID DATA FETCH
# ===============================
@st.cache_data(ttl=1800)
def fetch_data(symbol, exchange):

    # --- Try TwelveData first ---
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
                df.rename(columns={"close": "Close"}, inplace=True)
                return df, "TwelveData"

        except:
            pass

    # --- Fallback to yfinance ---
    try:
        ticker = symbol + (".NS" if exchange == "NSE" else ".BO")

        df = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            progress=False
        )

        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df[['Close']].dropna()
            return df, "yfinance"

    except:
        pass

    return None, None


# ===============================
# RUN ANALYSIS
# ===============================
if fetch_button:

    data, source = fetch_data(symbol, exchange)

    if data is None:
        st.error("No data available from TwelveData or yfinance.")
        st.stop()

    st.success(f"Data source: {source}")

    # ===============================
    # QUANT CALCULATIONS
    # ===============================
    data["Return"] = data["Close"].pct_change()
    data["MA20"] = data["Close"].rolling(20).mean()
    data["MA50"] = data["Close"].rolling(50).mean()

    annual_return = (
        data["Close"].iloc[-1] /
        data["Close"].iloc[0]
    ) - 1

    volatility = data["Return"].std() * np.sqrt(252)
    sharpe = annual_return / volatility if volatility != 0 else 0

    signal = "Buy" if data["MA20"].iloc[-1] > \
        data["MA50"].iloc[-1] else "Sell"

    score = 0
    if annual_return > 0:
        score += 1
    if volatility < 0.4:
        score += 1
    if sharpe > 1:
        score += 1
    if signal == "Buy":
        score += 1

    rating = (
        "Strong Buy" if score >= 3
        else "Watchlist" if score == 2
        else "Avoid"
    )

    # ===============================
    # DISPLAY METRICS
    # ===============================
    st.subheader("📈 Quant Stock Ratings")

    metrics = pd.DataFrame({
        "Stock": [f"{symbol} ({exchange})"],
        "Annual Return": [f"{annual_return*100:.2f}%"],
        "Volatility": [f"{volatility*100:.2f}%"],
        "Sharpe Ratio": [round(sharpe, 2)],
        "Signal": [signal],
        "Rating": [rating],
        "Score": [score]
    })

    st.dataframe(metrics, width="stretch")

    # ===============================
    # CHART
    # ===============================
    st.subheader("Price Chart")
    st.line_chart(data[["Close", "MA20", "MA50"]])

