# ======================================================
# INDIAN STOCK DASHBOARD – FULL AI + PORTFOLIO VERSION
# Features:
# - NSE + BSE full company list
# - Hybrid data (TwelveData optional + yfinance fallback)
# - Quant analysis (Return, Volatility, Sharpe, MA signals)
# - Portfolio tracker
# - Local AI analysis via Ollama
# - Dark professional UI
# ======================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import date
from twelvedata import TDClient

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Indian Stock Dashboard AI",
    page_icon="📈",
    layout="wide"
)

# ---------------- DARK UI ----------------
st.markdown("""
<style>
.main {background-color:#0e1117;}
section[data-testid="stSidebar"] {background-color:#111827;}
.section-title {font-size:24px;font-weight:600;margin-top:20px;margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Indian Stock + Portfolio AI Dashboard")

# ---------------- API SETUP ----------------
API_KEY = st.secrets.get("TWELVEDATA_API_KEY", None)
td = TDClient(apikey=API_KEY) if API_KEY else None

# ---------------- LOAD COMPANY LIST ----------------
@st.cache_data(ttl=86400)
def load_companies():
    frames = []

    # NSE FULL LIST
    try:
        nse = pd.read_csv(
            "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        )
        nse = nse[['NAME OF COMPANY','SYMBOL']]
        nse.columns = ['Company','Symbol']
        nse['Exchange'] = 'NSE'
        frames.append(nse)
    except:
        pass

    # BSE FULL LIST
    try:
        bse = pd.read_json(
            "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
        )
        bse = bse[['SCRIPNAME','SCRIP_CD']]
        bse.columns = ['Company','Symbol']
        bse['Exchange'] = 'BSE'
        bse['Symbol'] = bse['Symbol'].astype(str)
        frames.append(bse)
    except:
        pass

    # Combine NSE + BSE
    if frames:
        df = pd.concat(frames, ignore_index=True)
        df.drop_duplicates(subset=['Company','Exchange'], inplace=True)
        return df.sort_values('Company')

    # Fallback minimal list
    return pd.DataFrame({
        'Company':['Reliance Industries','TCS','Infosys'],
        'Symbol':['RELIANCE','TCS','INFY'],
        'Exchange':['NSE','NSE','NSE']
    })

companies_df = load_companies()

# ---------------- SIDEBAR ----------------
st.sidebar.header("⚙️ Controls")

exchange = st.sidebar.radio("Exchange", ["NSE","BSE"], horizontal=True)

filtered = companies_df[companies_df['Exchange']==exchange]

company = st.sidebar.selectbox("Search Company", filtered['Company'])

symbol = filtered.loc[
    filtered['Company']==company, 'Symbol'
].values[0]

start_date = st.sidebar.date_input("Start Date", date(2023,1,1))
end_date = st.sidebar.date_input("End Date", date.today())

fetch_button = st.sidebar.button("Fetch Data")

# ---------------- PORTFOLIO TRACKER ----------------
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(
        columns=['Symbol','Qty','Buy Price']
    )

st.sidebar.markdown("---")
st.sidebar.subheader("Portfolio")

new_symbol = st.sidebar.text_input("Symbol")
new_qty = st.sidebar.number_input("Qty", 0.0)
new_price = st.sidebar.number_input("Buy Price", 0.0)

if st.sidebar.button("Add to Portfolio"):
    new_row = pd.DataFrame([[new_symbol,new_qty,new_price]],
                           columns=['Symbol','Qty','Buy Price'])
    st.session_state.portfolio = pd.concat(
        [st.session_state.portfolio,new_row],
        ignore_index=True
    )

# ---------------- DATA FETCH ----------------
@st.cache_data(ttl=1800)
def fetch_data(symbol, exchange):

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
                    "open":"Open",
                    "high":"High",
                    "low":"Low",
                    "close":"Close"
                }, inplace=True)
                return df, "TwelveData"
        except:
            pass

    ticker = symbol + (".NS" if exchange=="NSE" else ".BO")

    try:
        df = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            progress=False
        )
        if not df.empty:
            return df, "yfinance"
    except:
        pass

    return None, None

# ---------------- AI FUNCTION ----------------
def ask_ai(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model":"llama3",
                "prompt":prompt,
                "stream":False
            }
        )
        return response.json()["response"]
    except Exception as e:
        return f"AI error: {e}"

# ---------------- MAIN ANALYSIS ----------------
if fetch_button:

    data, source = fetch_data(symbol, exchange)

    if data is None:
        st.error("No data available")
        st.stop()

    st.success(f"Data Source: {source}")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if "Close" not in data.columns:
        st.error("Close column missing")
        st.stop()

    data = data.dropna(subset=['Close'])

    # ----- QUANT METRICS -----
    data['Return'] = data['Close'].pct_change()
    data['MA20'] = data['Close'].rolling(20).mean()
    data['MA50'] = data['Close'].rolling(50).mean()

    annual_return = (data['Close'].iloc[-1]/data['Close'].iloc[0]) - 1
    volatility = data['Return'].std()*np.sqrt(252)
    sharpe = annual_return/volatility if volatility!=0 else 0

    signal = "BUY" if data['MA20'].iloc[-1] > data['MA50'].iloc[-1] else "SELL"

    # ----- METRICS DISPLAY -----
    st.markdown('<div class="section-title">Performance Metrics</div>', unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Annual Return", f"{annual_return*100:.2f}%")
    c2.metric("Volatility", f"{volatility*100:.2f}%")
    c3.metric("Sharpe", f"{sharpe:.2f}")
    c4.metric("Signal", signal)

    # ----- CHART -----
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=data.index,y=data['Close'],name="Price"))
    fig.add_trace(go.Scatter(x=data.index,y=data['MA20'],name="MA20"))
    fig.add_trace(go.Scatter(x=data.index,y=data['MA50'],name="MA50"))

    fig.update_layout(template="plotly_dark",height=600)
    st.plotly_chart(fig, use_container_width=True)

    # ----- AI ANALYSIS -----
    if st.button("AI Stock Insight"):
        prompt=f"""
        Analyze Indian stock:
        Symbol: {symbol}
        Return: {annual_return:.2%}
        Volatility: {volatility:.2%}
        Sharpe: {sharpe:.2f}
        Signal: {signal}

        Give professional analysis and suggestions.
        """

        st.write(ask_ai(prompt))

# ---------------- PORTFOLIO DISPLAY ----------------
st.markdown('<div class="section-title">Portfolio</div>', unsafe_allow_html=True)
st.dataframe(st.session_state.portfolio)

if st.button("AI Portfolio Review"):
    st.write(ask_ai(str(st.session_state.portfolio)))
