# =========================================================
# 📊 INDIAN MARKET INTELLIGENCE - PRO VERSION V5
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import datetime

# =========================================================
# 🎨 PAGE CONFIG
# =========================================================
st.set_page_config(page_title="Market Intelligence Pro", layout="wide")

st.markdown("""
<style>
body {background-color:#0f172a; color:white;}
.card {
    background:#1e293b;
    padding:15px;
    border-radius:12px;
    margin-bottom:10px;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Indian Market Intelligence PRO")

# =========================================================
# 📈 FETCH DATA
# =========================================================
def fetch_stock_data(symbol):
    df = yf.download(symbol, period="3mo", interval="1d")
    return df

# =========================================================
# 🧠 ADVANCED INDICATORS
# =========================================================
def add_advanced_indicators(df):

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))

    stoch_rsi = (rsi - rsi.rolling(14).min()) / (rsi.rolling(14).max() - rsi.rolling(14).min() + 1e-9)
    df['stoch_rsi'] = stoch_rsi * 100

    hh = df['High'].rolling(14).max()
    ll = df['Low'].rolling(14).min()
    df['williams_r'] = -100 * ((hh - df['Close']) / (hh - ll + 1e-9))

    obv = [0]
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['Close'].iloc[i-1]:
            obv.append(obv[-1] + df['Volume'].iloc[i])
        else:
            obv.append(obv[-1] - df['Volume'].iloc[i])
    df['obv'] = obv
    df['obv_slope'] = df['obv'].diff()

    vwap = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    df['vwap'] = vwap
    df['vwap_dev'] = (df['Close'] - df['vwap']) / df['vwap']

    dc_high = df['High'].rolling(20).max()
    dc_low = df['Low'].rolling(20).min()
    df['donchian_pos'] = ((df['Close'] - dc_low) / (dc_high - dc_low + 1e-9)) * 100

    df['ema20'] = df['Close'].ewm(span=20).mean()
    df['ema_slope'] = df['ema20'].diff()

    return df

# =========================================================
# 🎯 SCORING ENGINE
# =========================================================
def calculate_score(df):

    score = 0

    if df['stoch_rsi'].iloc[-1] > 80:
        score += 5
    elif df['stoch_rsi'].iloc[-1] < 20:
        score -= 3

    if df['williams_r'].iloc[-1] < -80:
        score += 4
    elif df['williams_r'].iloc[-1] > -20:
        score -= 4

    if df['obv_slope'].iloc[-1] > 0:
        score += 5
    else:
        score -= 3

    if df['vwap_dev'].iloc[-1] < -0.02:
        score += 4
    elif df['vwap_dev'].iloc[-1] > 0.03:
        score -= 5

    if df['donchian_pos'].iloc[-1] > 80:
        score += 5
    elif df['donchian_pos'].iloc[-1] < 20:
        score -= 3

    if df['ema_slope'].iloc[-1] > 0:
        score += 4
    else:
        score -= 3

    return score

# =========================================================
# 📊 STOCK LIST
# =========================================================
stocks = {
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "ITC": "ITC.NS",
    "L&T": "LT.NS",
    "SBI": "SBIN.NS"
}

results = []

# =========================================================
# 🚀 MAIN ENGINE
# =========================================================
for name, symbol in stocks.items():

    df = fetch_stock_data(symbol)

    if df.empty:
        continue

    df = add_advanced_indicators(df)

    score = calculate_score(df)

    last_price = df['Close'].iloc[-1]

    target = last_price * (1 + score / 100)
    stoploss = last_price * (1 - 0.02)

    results.append({
        "Stock": name,
        "Score": score,
        "Price": round(last_price, 2),
        "Target": round(target, 2),
        "Stoploss": round(stoploss, 2)
    })

# =========================================================
# 📋 DISPLAY
# =========================================================
df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)

st.subheader("📈 Short Term Opportunities (1 Week - 1 Month)")
st.dataframe(df_results)

# =========================================================
# 🧠 TOP PICK
# =========================================================
if not df_results.empty:
    best = df_results.iloc[0]

    st.markdown(f"""
    <div class="card">
    <h3>🔥 Top Pick: {best['Stock']}</h3>
    Score: {best['Score']}<br>
    Price: ₹{best['Price']}<br>
    Target: ₹{best['Target']}<br>
    Stoploss: ₹{best['Stoploss']}
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# ⏱ AUTO REFRESH
# =========================================================
st.caption("Auto-updating intelligence system")
