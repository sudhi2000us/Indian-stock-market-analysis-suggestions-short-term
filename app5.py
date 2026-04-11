# =========================================================
# 📊 INDIAN MARKET INTELLIGENCE - PRO V7 (UI FIXED)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="Market Intelligence PRO", layout="wide")

# =========================================================
# 🎨 MODERN UI THEME (FIXED READABILITY)
# =========================================================
st.markdown("""
<style>
body {
    background-color: #0b1220;
    color: #e5e7eb;
}

h1, h2, h3 {
    color: #ffffff;
}

.card {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    padding: 20px;
    border-radius: 14px;
    color: #f1f5f9;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
}

.top-card {
    background: linear-gradient(135deg, #1d4ed8, #1e40af);
    padding: 25px;
    border-radius: 16px;
    color: white;
    font-size: 16px;
}

table {
    color: white !important;
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

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[['Open','High','Low','Close','Volume']].copy()
    df.dropna(inplace=True)

    return df

# =========================================================
# 🧠 INDICATORS
# =========================================================
def add_indicators(df):

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))

    df['stoch_rsi'] = ((rsi - rsi.rolling(14).min()) /
                      (rsi.rolling(14).max() - rsi.rolling(14).min() + 1e-9)) * 100

    hh = df['High'].rolling(14).max()
    ll = df['Low'].rolling(14).min()
    df['williams_r'] = -100 * ((hh - df['Close']) / (hh - ll + 1e-9))

    close = df['Close'].values
    volume = df['Volume'].values

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

    vwap = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    df['vwap_dev'] = (df['Close'] - vwap) / vwap

    dc_high = df['High'].rolling(20).max()
    dc_low = df['Low'].rolling(20).min()
    df['donchian_pos'] = ((df['Close'] - dc_low) / (dc_high - dc_low + 1e-9)) * 100

    df['ema20'] = df['Close'].ewm(span=20).mean()
    df['ema_slope'] = df['ema20'].diff()

    return df

# =========================================================
# 🎯 SCORING
# =========================================================
def calculate_score(df):

    score = 0

    if df['stoch_rsi'].iloc[-1] > 70: score += 3
    if df['williams_r'].iloc[-1] < -80: score += 3
    if df['obv_slope'].iloc[-1] > 0: score += 4
    if df['vwap_dev'].iloc[-1] < -0.01: score += 2
    if df['donchian_pos'].iloc[-1] > 70: score += 3
    if df['ema_slope'].iloc[-1] > 0: score += 3

    return score

# =========================================================
# 📊 STOCKS
# =========================================================
stocks = {
    "ITC": "ITC.NS",
    "TCS": "TCS.NS",
    "L&T": "LT.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "SBI": "SBIN.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Titan": "TITAN.NS",
    "Infosys": "INFY.NS",
    "Reliance": "RELIANCE.NS"
}

results = []

# =========================================================
# 🚀 MAIN LOOP
# =========================================================
for name, symbol in stocks.items():

    df = fetch_stock_data(symbol)

    if df.empty or len(df) < 30:
        continue

    df = add_indicators(df)
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

    # Highlight table
    st.dataframe(
        df_results.style.background_gradient(cmap="Blues"),
        use_container_width=True
    )

    best = df_results.iloc[0]

    st.markdown(f"""
    <div class="top-card">
    🔥 <b>Top Pick: {best['Stock']}</b><br><br>
    Score: <b>{best['Score']}</b><br>
    Price: ₹{best['Price']}<br>
    Target: ₹{best['Target']}<br>
    Stoploss: ₹{best['Stoploss']}
    </div>
    """, unsafe_allow_html=True)

else:
    st.warning("No strong opportunities found today.")

st.caption("AI-driven market intelligence running...")
