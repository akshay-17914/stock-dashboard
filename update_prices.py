import pandas as pd
import yfinance as yf
import os
import time

print("🚀 Starting Ultra-Fast NSE Batch Price Update...")

# ---------------- LOAD NSE UNIVERSE ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
universe_file = os.path.join(BASE_DIR, "nse_universe.csv")

try:
    stocks = pd.read_csv(universe_file)
    symbols = stocks["Symbol"].dropna().unique()
except Exception as e:
    print("❌ Universe file missing:", e)
    exit()

# Convert to Yahoo format
tickers = [symbol + ".NS" for symbol in symbols]

# ---------------- CREATE DATABASE FOLDER ----------------
price_db_path = os.path.join(BASE_DIR, "price_db")
os.makedirs(price_db_path, exist_ok=True)

# ---------------- BATCH SETTINGS ----------------
BATCH_SIZE = 50   # 50 tickers per request
TOTAL = len(tickers)

print(f"Total Stocks: {TOTAL}")
print(f"Batch Size: {BATCH_SIZE}")

# ---------------- DOWNLOAD IN BATCHES ----------------
for i in range(0, TOTAL, BATCH_SIZE):

    batch = tickers[i:i+BATCH_SIZE]

    print(f"📦 Downloading batch {i} to {i+len(batch)}")

    try:
        df = yf.download(
            batch,
            period="5d",
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False
        )

        for ticker in batch:
            symbol = ticker.replace(".NS", "")
            file_path = os.path.join(price_db_path, f"{symbol}.csv")

            try:
                if ticker not in df:
                    continue

                stock_df = df[ticker].dropna()

                if stock_df.empty:
                    continue

                if os.path.exists(file_path):
                    old = pd.read_csv(file_path, index_col=0, parse_dates=True)
                    stock_df = pd.concat([old, stock_df]).drop_duplicates()

                stock_df.to_csv(file_path)

            except:
                continue

        time.sleep(1)  # small pause to avoid rate limit

    except Exception as e:
        print("Batch failed:", e)

print("✅ Ultra-Fast Daily Update Completed")