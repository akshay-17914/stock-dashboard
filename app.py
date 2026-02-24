# ======================================================
# INDIAN STOCK DASHBOARD (NSE + BSE FULL)
# TwelveData API Version (Production Safe)
# ======================================================

import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import date
from twelvedata import TDClient

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(page_title="Indian Stock Dashboard", layout="wide")
st.title("📊 Indian Stock Analysis Dashboard")

# ===============================
# API KEY (SECURE FROM STREAMLIT)
# ===============================
API_KEY = st.secrets["TWELVEDATA_API_KEY"]
td = TDClient(apikey=API_KEY)

# ===============================
# LOAD NSE + BSE COMPANY LIST
# ===============================
@st.cache_data(ttl=86400)
def load_companies():

    frames = []

    # NSE companies
    try:
        nse = pd.read_csv(
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        )

        nse = nse[['NAME OF COMPANY', 'SYMBOL']]
        nse['Exchange'] = "NSE"

        frames.append(
            nse.rename(columns={
                "NAME OF COMPANY": "Company",
                "SYMBOL": "Symbol"
            })
        )
    except:
        pass

    # Simple fallback if BSE list unavailable
    # (BSE official API is unstable for cloud apps)
    try:
        bse = pd.read_csv(
            "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        )

        bse = bse[['Name','Symbol']]
        bse['Exchange'] = "BSE"

        frames.append(
            bse.rename(columns={
                "Name":"Company"
            })
        )
    except:
        pass

    if frames:
        return pd.concat(frames).drop_duplicates().sort_values("Company")

    return pd.DataFrame({
        "Company":["Reliance Industries"],
        "Symbol":["RELIANCE"],
        "Exchange":["NSE"]
    })


companies_df = load_companies()

# ===============================
# SIDEBAR SETTINGS
# ===============================
st.sidebar.header("🔎 Stock Settings")

exchange = st.sidebar.radio(
    "Exchange",
    ["NSE", "BSE"],
    horizontal=True
)

filtered = companies_df[companies_df["Exchange"] == exchange]

company = st.sidebar.selectbox(
    "Search Company",
    filtered["Company"]
)

symbol = filtered.loc[
    filtered["Company"] == company,
    "Symbol"
].values[0]

start_date = st.sidebar.date_input("Start Date", date(2023,1,1))
end_date = st.sidebar.date_input("End Date", date.today())

# Prevent excessive API refresh
fetch_button = st.sidebar.button("Fetch Data")

# ===============================
# FETCH DATA SAFELY
# ===============================
@st.cache_data(ttl=3600)
def get_data(symbol, exchange):

    try:
        ts = td.time_series(
            symbol=symbol,
            exchange=exchange,
            interval="1day",
            outputsize=500
        )

        df = ts.as_pandas()

        if df is None or df.empty:
            return None

        df = df.sort_index()
        return df

    except Exception as e:
        return str(e)


if fetch_button:

    data = get_data(symbol, exchange)

    if isinstance(data, str):
        st.error("API Error:")
        st.code(data)
        st.stop()

    if data is None:
        st.error("No data returned.")
        st.stop()

    data.rename(columns={"close": "Close"}, inplace=True)

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

    # ===============================
    # SCORING SYSTEM
    # ===============================
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
    # METRICS DISPLAY
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

    st.dataframe(metrics, use_container_width=True)

    # ===============================
    # PRICE CHART
    # ===============================
    st.subheader("Price Chart")
    st.line_chart(data[["Close", "MA20", "MA50"]])

