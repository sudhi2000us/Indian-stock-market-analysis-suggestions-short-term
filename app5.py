# =========================================================
# 📊 INDIAN MARKET INTELLIGENCE PRO V12 (FULL SYSTEM)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Market Intelligence PRO", layout="wide")

# 🔄 AUTO REFRESH EVERY 5 MIN
st_autorefresh(interval=300000, key="refresh")

NEWS_API_KEY = "2e99f73f7e4346c08f94c6d464bf7315"

# =========================================================
# 🎨 UI
# =========================================================
st.markdown("""
<style>
body {background:#f5f7fb;}
.card {
    background:white;
    padding:16px;
    border-radius:10px;
    box-shadow:0 4px 10px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Market Intelligence PRO V12")

# =========================================================
# 🧼 CLEAN DF
# =========================================================
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# =========================================================
# 🌍 GLOBAL SCORE
# =========================================================
def global_score():
    indices = ["^GSPC","^IXIC","^DJI","^N225","^HSI"]
    score = 0
    for i in indices:
        df = yf.download(i, period="2d")
        if len(df)>1:
            df=clean_df(df)
            c=df['Close'].values
            score += 2 if c[-1]>c[-2] else -2
    return score

# =========================================================
# 📰 NEWS SCORE
# =========================================================
def news_score():
    try:
        url=f"https://newsapi.org/v2/everything?q=stock%20market&apiKey={NEWS_API_KEY}"
        data=requests.get(url).json()
        headlines=[a['title'].lower() for a in data.get("articles",[])]
    except:
        return 0

    neg=["war","conflict","inflation","crisis","attack","recession"]
    pos=["growth","deal","recovery","bullish","positive"]

    score=0
    for h in headlines:
        for w in neg:
            if w in h: score-=2
        for w in pos:
            if w in h: score+=2

    return max(min(score,10),-10)

# =========================================================
# 🌅 PRE-MARKET (GIFT NIFTY PROXY)
# =========================================================
def premarket():
    us = global_score()
    asia = yf.download("^N225", period="2d")
    asia_score = 0
    if len(asia)>1:
        asia=clean_df(asia)
        c=asia['Close'].values
        asia_score = 2 if c[-1]>c[-2] else -2

    total = us + asia_score

    if total > 2:
        return "BULLISH"
    elif total < -2:
        return "BEARISH"
    return "SIDEWAYS"

# =========================================================
# 🏦 SECTOR RANKING
# =========================================================
sectors = {
    "BANK":["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS"],
    "IT":["TCS.NS","INFY.NS"],
    "FMCG":["ITC.NS"],
    "INFRA":["LT.NS"],
    "CONS":["TITAN.NS"]
}

def sector_strength():
    result={}
    for s,stocks in sectors.items():
        sc=0
        for stk in stocks:
            df=yf.download(stk, period="2d")
            if len(df)>1:
                df=clean_df(df)
                c=df['Close'].values
                sc += 1 if c[-1]>c[-2] else -1
        result[s]=sc
    return sorted(result.items(), key=lambda x:x[1], reverse=True)

# =========================================================
# 📊 INDICATORS
# =========================================================
def indicators(df):
    df['ema20']=df['Close'].ewm(span=20).mean()
    df['ema_slope']=df['ema20'].diff()
    df['rsi']=100-(100/(1+(df['Close'].diff().clip(lower=0).rolling(14).mean() /
                             (df['Close'].diff().clip(upper=0).abs().rolling(14).mean()+1e-9))))
    return df

# =========================================================
# 🎯 STOCK SCORE + OPTIONS SIGNAL
# =========================================================
def analyze(df):
    score=0
    signal="NEUTRAL"

    if df['ema_slope'].iloc[-1]>0:
        score+=3
        signal="CE BUY"

    if df['rsi'].iloc[-1]<40:
        score+=2

    if df['ema_slope'].iloc[-1]<0:
        score-=3
        signal="PE BUY"

    return score, signal

# =========================================================
# 📊 STOCKS
# =========================================================
stocks={
"ITC":"ITC.NS","TCS":"TCS.NS","L&T":"LT.NS",
"ICICI":"ICICIBANK.NS","SBI":"SBIN.NS",
"HDFC":"HDFCBANK.NS","Titan":"TITAN.NS"
}

# =========================================================
# 🚀 MAIN ENGINE
# =========================================================
g=global_score()
n=news_score()
pm=premarket()

col1,col2,col3=st.columns(3)

col1.metric("🌍 Global", g)
col2.metric("📰 News", n)
col3.metric("🌅 Pre-Market", pm)

# =========================================================
# 📊 SECTOR PANEL
# =========================================================
st.subheader("🏭 Sector Strength")
sector_data=sector_strength()
st.write(sector_data)

# =========================================================
# 📊 STOCK ANALYSIS
# =========================================================
results=[]

for name,symbol in stocks.items():

    df=yf.download(symbol, period="3mo")
    if len(df)<30: continue

    df=clean_df(df)
    df=df[['Open','High','Low','Close','Volume']]
    df=indicators(df)

    s,signal=analyze(df)

    final = s + (g*0.2) + (n*0.2)

    price=df['Close'].iloc[-1]

    results.append({
        "Stock":name,
        "Score":round(final,2),
        "Signal":signal,
        "Price":round(price,2),
        "Target":round(price*1.03,2),
        "Stoploss":round(price*0.97,2)
    })

# =========================================================
# 📋 OUTPUT
# =========================================================
df_out=pd.DataFrame(results).sort_values(by="Score",ascending=False)

st.subheader("📈 Trade Opportunities")
st.dataframe(df_out, use_container_width=True)

# =========================================================
# 🔥 TOP PICK + CHART
# =========================================================
best=df_out.iloc[0]

st.subheader(f"🔥 Top Pick: {best['Stock']}")

st.write(best)

# TradingView Chart
st.components.v1.html(f"""
<iframe src="https://s.tradingview.com/widgetembed/?symbol=NSE:{best['Stock']}&interval=60&theme=light"
width="100%" height="400"></iframe>
""", height=420)

# =========================================================
# ⚠️ STRATEGY
# =========================================================
if n < -5:
    st.warning("Risk-off: Prefer defensive stocks")
elif n > 5:
    st.success("Risk-on: Aggressive trades allowed")

st.caption("Auto-refresh every 5 minutes • Hedge-level intelligence")
