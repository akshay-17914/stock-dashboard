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

# ===============================
# API KEY (FROM STREAMLIT SECRETS)
# ===============================
API_KEY = st.secrets["TWELVEDATA_API_KEY"]
td = TDClient(apikey=API_KEY)

# ===============================
# LOAD ALL NSE + BSE COMPANIES
# ===============================
@st.cache_data(ttl=86400)
def load_companies():

    frames = []

    # NSE Companies
    try:
        nse = pd.read_csv(
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        )
        nse = nse[['NAME OF COMPANY', 'SYMBOL']]
        nse['Exchange'] = "NSE"
        frames.append(nse.rename(columns={
            "NAME OF COMPANY": "Company",
            "SYMBOL": "Symbol"
        }))
    except:
        pass

    # BSE Companies (public dataset mirror)
    try:
        bse = pd.read_csv(
            "https://raw.githubusercontent.com/atulprakash-stock/BSE-dataset/main/bse_equity.csv"
        )
        bse = bse[['Security Name', 'Security Id']]
        bse['Exchange'] = "BSE"
        frames.append(bse.rename(columns={
            "Security Name": "Company",
            "Security Id": "Symbol"
        }))
    except:
        pass

    if frames:
        df = pd.concat(frames).drop_duplicates()
        return df.sort_values("Company")

    # fallback
    return pd.DataFrame({
        "Company": ["Reliance Industries", "TCS"],
        "Symbol": ["RELIANCE", "TCS"],
        "Exchange": ["NSE", "NSE"]
    })

companies_df = load_companies()

# ===============================
# SIDEBAR SETTINGS
# ===============================
st.sidebar.title("🔎 Stock Settings")

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

auto_refresh = st.sidebar.slider(
    "Auto Refresh (seconds)",
    0, 600, 0
)

start_date = st.sidebar.date_input("Start Date", date(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", date.today())

# ===============================
# FETCH DATA FROM TWELVEDATA
# ===============================
@st.cache_data(ttl=600)
def get_data(symbol, exchange):

    ts = td.time_series(
        symbol=symbol,
        exchange=exchange,
        interval="1day",
        outputsize=500
    )

    df = ts.as_pandas()
    df = df.sort_index()

    return df

data = get_data(symbol, exchange)

# ===============================
# MAIN DASHBOARD
# ===============================
st.title("📊 Indian Stock Analysis Dashboard")

if data.empty:
    st.error("No data found.")
    st.stop()

data.rename(columns={"close": "Close"}, inplace=True)

# ===============================
# QUANT CALCULATIONS
# ===============================
data["Return"] = data["Close"].pct_change()
data["MA20"] = data["Close"].rolling(20).mean()
data["MA50"] = data["Close"].rolling(50).mean()

annual_return = (data["Close"].iloc[-1] /
                 data["Close"].iloc[0]) - 1

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
# CHART
# ===============================
st.subheader("Price Chart")
st.line_chart(data[["Close", "MA20", "MA50"]])

# ===============================
# AUTO REFRESH
# ===============================
if auto_refresh > 0:
    time.sleep(auto_refresh)
    st.rerun()
