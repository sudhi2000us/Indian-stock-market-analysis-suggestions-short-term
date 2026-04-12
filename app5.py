# =========================================================
# 📊 INDIAN MARKET INTELLIGENCE - PRO V10 (HEDGE FUND)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests

st.set_page_config(page_title="Market Intelligence PRO", layout="wide")

# =========================================================
# 🔐 CONFIG
# =========================================================
NEWS_API_KEY = "YOUR_API_KEY"

# =========================================================
# 🎨 MODERN UI
# =========================================================
st.markdown("""
<style>
body {background:#0b1220; color:#e5e7eb;}
.card {
    background: linear-gradient(135deg,#1e293b,#0f172a);
    padding:20px;
    border-radius:14px;
    margin-bottom:10px;
}
.metric {
    font-size:22px;
    font-weight:bold;
}
.good {color:#22c55e;}
.bad {color:#ef4444;}
.neutral {color:#facc15;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Market Intelligence PRO V10")

# =========================================================
# 🧼 CLEAN DF
# =========================================================
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# =========================================================
# 🌍 GLOBAL MARKETS
# =========================================================
def global_score():
    indices = ["^GSPC","^IXIC","^DJI","^N225","^HSI"]
    score = 0

    for symbol in indices:
        df = yf.download(symbol, period="2d")
        if df.empty or len(df)<2: continue

        df = clean_df(df)
        close = df['Close'].values

        score += 2 if close[-1] > close[-2] else -2

    return score

# =========================================================
# 📰 NEWS
# =========================================================
def fetch_news():
    url = f"https://newsapi.org/v2/everything?q=stock%20market%20india&language=en&pageSize=20&apiKey={2e99f73f7e4346c08f94c6d464bf7315}"
    try:
        data = requests.get(url).json()
        return [a['title'].lower() for a in data.get("articles",[])]
    except:
        return []

def news_score():

    headlines = fetch_news()

    negative = ["war","conflict","attack","tension","inflation","rate hike","crisis","oil","fear","recession","failed"]
    positive = ["deal","growth","recovery","positive","bullish","agreement","rate cut"]

    score = 0

    for h in headlines:
        for w in negative:
            if w in h: score -= 2
        for w in positive:
            if w in h: score += 2

    return score

# =========================================================
# 🏦 SECTOR ROTATION
# =========================================================
def sector_score(symbol):

    sectors = {
        "BANK":["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS"],
        "IT":["TCS.NS","INFY.NS"],
        "FMCG":["ITC.NS"],
        "INFRA":["LT.NS"],
        "CONS":["TITAN.NS"]
    }

    for s,stocks in sectors.items():
        if symbol in stocks:
            sc=0
            for stk in stocks:
                df = yf.download(stk, period="2d")
                if len(df)>1:
                    df=clean_df(df)
                    c=df['Close'].values
                    sc += 1 if c[-1]>c[-2] else -1
            return sc
    return 0

# =========================================================
# 📊 INDICATORS
# =========================================================
def indicators(df):

    df['ema20'] = df['Close'].ewm(span=20).mean()
    df['ema_slope'] = df['ema20'].diff()

    df['rsi'] = 100 - (100/(1+(df['Close'].diff().clip(lower=0).rolling(14).mean() /
                                 (df['Close'].diff().clip(upper=0).abs().rolling(14).mean()+1e-9))))

    df['stoch'] = ((df['rsi']-df['rsi'].rolling(14).min()) /
                   (df['rsi'].rolling(14).max()-df['rsi'].rolling(14).min()+1e-9))*100

    return df

# =========================================================
# 🎯 STOCK SCORE
# =========================================================
def stock_score(df):
    s=0
    if df['stoch'].iloc[-1]>60: s+=3
    if df['ema_slope'].iloc[-1]>0: s+=3
    return s

# =========================================================
# 📊 STOCK LIST
# =========================================================
stocks={
"ITC":"ITC.NS","TCS":"TCS.NS","L&T":"LT.NS",
"ICICI":"ICICIBANK.NS","SBI":"SBIN.NS",
"HDFC":"HDFCBANK.NS","Titan":"TITAN.NS"
}

# =========================================================
# 🚀 MAIN ENGINE
# =========================================================
g = global_score()
n = news_score()

col1,col2,col3 = st.columns(3)

with col1:
    st.markdown(f'<div class="card"><div class="metric">🌍 Global Score<br>{g}</div></div>',unsafe_allow_html=True)

with col2:
    st.markdown(f'<div class="card"><div class="metric">📰 News Score<br>{n}</div></div>',unsafe_allow_html=True)

risk = "LOW"
if n < -5: risk = "HIGH"
elif g < -5: risk = "HIGH"

with col3:
    st.markdown(f'<div class="card"><div class="metric">⚠️ Risk<br>{risk}</div></div>',unsafe_allow_html=True)

results=[]

for name,symbol in stocks.items():

    df = yf.download(symbol, period="3mo")
    if df.empty or len(df)<30: continue

    df = clean_df(df)
    df = df[['Open','High','Low','Close','Volume']]

    df = indicators(df)

    s = stock_score(df)
    sec = sector_score(symbol)

    final = (s*0.4)+(sec*0.2)+(g*0.2)+(n*0.2)

    price = df['Close'].iloc[-1]
    target = price*(1+final/100)
    sl = price*0.97
    conf = min(100,max(50,final*5))

    results.append({
        "Stock":name,
        "Score":round(final,2),
        "Confidence":conf,
        "Price":round(price,2),
        "Target":round(target,2),
        "Stoploss":round(sl,2)
    })

# =========================================================
# 📋 OUTPUT
# =========================================================
if results:

    df_out = pd.DataFrame(results).sort_values(by="Score",ascending=False)

    st.subheader("📈 Trade Opportunities")
    st.dataframe(df_out,use_container_width=True)

    best = df_out.iloc[0]

    st.markdown(f"""
    <div class="card">
    🔥 <b>Top Pick: {best['Stock']}</b><br><br>
    Confidence: {best['Confidence']}%<br>
    Target: ₹{best['Target']}<br>
    Stoploss: ₹{best['Stoploss']}
    </div>
    """,unsafe_allow_html=True)

    if risk=="HIGH":
        st.error("⚠️ Market Risk High — Avoid Aggressive Trading")

else:
    st.warning("No trades today")

st.caption("Hedge-fund style intelligence engine running...")
