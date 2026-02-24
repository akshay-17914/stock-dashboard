# ======================================================
# INDIAN STOCK DASHBOARD (NSE + BSE)
# Simple Quant Dashboard with:
# - Company name search selector
# - Sharpe / Return / Volatility scoring
# - Automatic Buy/Sell rating
# - Live refresh chart with MA signals
# ======================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import date
import time

st.set_page_config(page_title="Indian Stock Dashboard", layout="wide")
st.title("📊 Indian Stock Analysis Dashboard")

st.markdown("""
Features:
- NSE + BSE company search
- Quant scoring (Return, Volatility, Sharpe)
- Automatic Buy/Sell rating
- Moving-average signal visualization
- Auto-refresh charts
""")

# ======================================================
# LOAD NSE + BSE COMPANY LIST
# ======================================================

@st.cache_data
def load_companies():
    frames = []

    try:
        nse = pd.read_csv("https://archives.nseindia.com/content/equities/EQUITY_L.csv")
        nse = nse[['NAME OF COMPANY','SYMBOL']].dropna()
        nse['Ticker'] = nse['SYMBOL'] + '.NS'
        frames.append(nse[['NAME OF COMPANY','Ticker']])
    except:
        pass

    try:
        bse = pd.read_json("https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w")
        bse = bse[['SCRIPNAME','SCRIP_CD']]
        bse.columns = ['NAME OF COMPANY','Ticker']
        bse['Ticker'] = bse['Ticker'].astype(str) + '.BO'
        frames.append(bse)
    except:
        pass

    if frames:
        df = pd.concat(frames).drop_duplicates()
        return df.sort_values('NAME OF COMPANY')

    return pd.DataFrame({
        'NAME OF COMPANY':['Reliance Industries','TCS','Infosys'],
        'Ticker':['RELIANCE.NS','TCS.NS','INFY.NS']
    })

company_df = load_companies()
company_map = dict(zip(company_df['NAME OF COMPANY'], company_df['Ticker']))

# ======================================================
# SIDEBAR SETTINGS
# ======================================================

st.sidebar.header("🔎 Search Stocks")

selected_companies = st.sidebar.multiselect(
    "Search company name",
    options=list(company_map.keys())
)

selected_stocks = [company_map[c] for c in selected_companies]

refresh_sec = st.sidebar.slider("Auto Refresh Seconds", 15, 300, 60)
start_date = st.sidebar.date_input("Start Date", date(2023,1,1))
end_date = st.sidebar.date_input("End Date", date.today())

# ======================================================
# ANALYSIS FUNCTION
# ======================================================

@st.cache_data(ttl=60)
def analyze_stock(symbol,start,end):
    df = yf.download(symbol,start=start,end=end,progress=False)

    if df.empty:
        return None

    if isinstance(df.columns,pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[['Close']].dropna()

    df['log_return'] = np.log(df['Close']/df['Close'].shift(1))

    annual_return = df['log_return'].mean()*252
    volatility = df['log_return'].std()*np.sqrt(252)

    sharpe = np.nan
    if volatility!=0:
        sharpe = annual_return/volatility

    # Moving average signals
    df['ma20']=df['Close'].rolling(20).mean()
    df['ma50']=df['Close'].rolling(50).mean()

    signal="Neutral"
    if df['ma20'].iloc[-1] > df['ma50'].iloc[-1]:
        signal="Buy"
    else:
        signal="Sell"

    # Quant rating score
    score=0

    if sharpe>1:
        score+=2
    elif sharpe>0.5:
        score+=1

    if annual_return>0.15:
        score+=2
    elif annual_return>0.08:
        score+=1

    if volatility<0.2:
        score+=1

    rating="Avoid"
    if score>=5:
        rating="Strong Buy"
    elif score>=3:
        rating="Watchlist"

    return {
        "Stock":symbol,
        "Return":annual_return,
        "Volatility":volatility,
        "Sharpe":sharpe,
        "Signal":signal,
        "Rating":rating,
        "Score":score,
        "Data":df
    }

# ======================================================
# RUN ANALYSIS
# ======================================================

results=[]

for stock in selected_stocks:
    r=analyze_stock(stock,start_date,end_date)
    if r:
        results.append(r)

# ======================================================
# DISPLAY TABLE
# ======================================================

if results:
    table=pd.DataFrame([
        {
            "Stock":r['Stock'],
            "Annual Return":r['Return'],
            "Volatility":r['Volatility'],
            "Sharpe":r['Sharpe'],
            "Signal":r['Signal'],
            "Rating":r['Rating'],
            "Score":r['Score']
        }
        for r in results
    ])

    table=table.sort_values("Score",ascending=False)

    st.subheader("📈 Quant Stock Ratings")
    st.dataframe(table.style.format({
        "Annual Return":"{:.2%}",
        "Volatility":"{:.2%}",
        "Sharpe":"{:.2f}"
    }))

    for r in results:
        st.subheader(r['Stock'])
        st.write("Rating:",r['Rating'],"| Score:",r['Score'],"| Signal:",r['Signal'])
        st.line_chart(r['Data'][['Close','ma20','ma50']].dropna())

st.caption(f"Auto refresh every {refresh_sec} seconds")

time.sleep(refresh_sec)
st.rerun()