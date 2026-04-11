# =========================================================
# 📊 INDIAN MARKET INTELLIGENCE - PRO V6 (STABLE)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Market Intelligence PRO", layout="wide")

# =========================================================
# 🎨 UI STYLE
# =========================================================
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

    if df.empty:
        return df

    # Fix multi-index issue
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[['Open','High','Low','Close','Volume']].copy()
    df.dropna(inplace=True)

    return df

# =========================================================
# 🧠 ADVANCED INDICATORS (FIXED)
# =========================================================
def add_advanced_indicators(df):

    # RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))

    # Stoch RSI
    stoch_rsi = (rsi - rsi.rolling(14).min()) / (rsi.rolling(14).max() - rsi.rolling(14).min() + 1e-9)
    df['stoch_rsi'] = stoch_rsi * 100

    # Williams %R
    hh = df['High'].rolling(14).max()
    ll = df['Low'].rolling(14).min()
    df['williams_r'] = -100 * ((hh - df['Close']) / (hh - ll + 1e-9))

    # OBV (FIXED)
    close = df['Close'].astype(float).values
    volume = df['Volume'].astype(float).values

    obv = [0]
    for i in range(1, len(close)):
        if close[i] > close[i-1]:
            obv.append(obv[-1] + volume[i])
        elif close[i] < close[i-1]:
            obv.append(obv[-1] - volume[i])
        else:
            obv.append(obv[-1])

    df['obv'] = obv
    df['obv_slope'] = pd.Series(obv).diff()

    # VWAP
    vwap = (df['Close'] * df['Volume']).cumsum() / (df['Volume'].cumsum() + 1e-9)
    df['vwap'] = vwap
    df['vwap_dev'] = (df['Close'] - df['vwap']) / df['vwap']

    # Donchian
    dc_high = df['High'].rolling(20).max()
    dc_low = df['Low'].rolling(20).min()
    df['donchian_pos'] = ((df['Close'] - dc_low) / (dc_high - dc_low + 1e-9)) * 100

    # EMA slope
    df['ema20'] = df['Close'].ewm(span=20).mean()
    df['ema_slope'] = df['ema20'].diff()

    return df

# =========================================================
# 🎯 SCORING ENGINE (BALANCED)
# =========================================================
def calculate_score(df):

    score = 0

    stoch = df['stoch_rsi'].iloc[-1]
    will = df['williams_r'].iloc[-1]
    obv = df['obv_slope'].iloc[-1]
    vwap = df['vwap_dev'].iloc[-1]
    donch = df['donchian_pos'].iloc[-1]
    ema = df['ema_slope'].iloc[-1]

    # Relaxed scoring
    if stoch > 70:
        score += 3
    elif stoch < 30:
        score -= 2

    if will < -80:
        score += 3
    elif will > -20:
        score -= 3

    if obv > 0:
        score += 4

    if vwap < -0.01:
        score += 2
    elif vwap > 0.04:
        score -= 3

    if donch > 70:
        score += 3

    if ema > 0:
        score += 3

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
    "SBI": "SBIN.NS",
    "Titan": "TITAN.NS"
}

results = []

# =========================================================
# 🚀 MAIN ENGINE
# =========================================================
for name, symbol in stocks.items():

    df = fetch_stock_data(symbol)

    if df.empty or len(df) < 30:
        continue

    df = add_advanced_indicators(df)

    score = calculate_score(df)

    price = df['Close'].iloc[-1]

    target = price * (1 + score / 100)
    stoploss = price * 0.97

    results.append({
        "Stock": name,
        "Score": score,
        "Price": round(price, 2),
        "Target": round(target, 2),
        "Stoploss": round(stoploss, 2)
    })

# =========================================================
# 📋 DISPLAY
# =========================================================
if results:

    df_results = pd.DataFrame(results).sort_values(by="Score", ascending=False)

    st.subheader("📈 Short Term Opportunities (1 Week - 1 Month)")
    st.dataframe(df_results, use_container_width=True)

    # Top pick safe handling
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

else:
    st.warning("No strong opportunities found today.")

# =========================================================
# ⏱ AUTO REFRESH
# =========================================================
st.caption("AI-driven market intelligence running...")
