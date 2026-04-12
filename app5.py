# =========================================================
# 📊 MARKET INTELLIGENCE PRO V13 (FIXED PROFESSIONAL UI)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(layout="wide")

# 🔄 Auto refresh every 5 min
st_autorefresh(interval=300000, key="refresh")

NEWS_API_KEY = "2e99f73f7e4346c08f94c6d464bf7315"

# =========================================================
# 🎨 CLEAN UI
# =========================================================
st.markdown("""
<style>
.main {background:#f4f6fb;}
.card {
    background:white;
    padding:16px;
    border-radius:12px;
    box-shadow:0 3px 10px rgba(0,0,0,0.08);
}
.title {font-size:22px;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

st.title("📊 Market Intelligence PRO")

# =========================================================
# 🧼 CLEAN DF
# =========================================================
def clean(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# =========================================================
# 🌍 GLOBAL SCORE
# =========================================================
def global_score():
    indices = ["^GSPC","^IXIC","^DJI"]
    score = 0
    for i in indices:
        df = yf.download(i, period="2d")
        if len(df)>1:
            df=clean(df)
            c=df['Close'].values
            score += 2 if c[-1]>c[-2] else -2
    return score

# =========================================================
# 📰 NEWS SCORE
# =========================================================
def news_score():
    try:
        url=f"https://newsapi.org/v2/everything?q=market&apiKey={NEWS_API_KEY}"
        data=requests.get(url).json()
        headlines=[a['title'].lower() for a in data.get("articles",[])]
    except:
        return 0

    neg=["war","conflict","inflation","crisis","attack"]
    pos=["growth","deal","positive"]

    score=0
    for h in headlines:
        for w in neg:
            if w in h: score-=2
        for w in pos:
            if w in h: score+=2

    return max(min(score,10),-10)

# =========================================================
# 🏭 SECTOR STRENGTH (FIXED)
# =========================================================
sectors = {
    "BANK":["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS"],
    "IT":["TCS.NS","INFY.NS"],
    "FMCG":["ITC.NS"],
    "INFRA":["LT.NS"],
    "CONSUMPTION":["TITAN.NS"]
}

def sector_strength():
    data=[]
    for s,stocks in sectors.items():
        score=0
        for stk in stocks:
            df=yf.download(stk, period="2d")
            if len(df)>1:
                df=clean(df)
                c=df['Close'].values
                score += 1 if c[-1]>c[-2] else -1
        data.append([s,score])
    df=pd.DataFrame(data, columns=["Sector","Score"])
    return df.sort_values(by="Score",ascending=False)

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
# 🎯 ANALYSIS
# =========================================================
def analyze(df):
    score=0
    signal="NO TRADE"

    if df['ema_slope'].iloc[-1]>0:
        score+=3
        signal="BUY CE"

    if df['ema_slope'].iloc[-1]<0:
        score-=3
        signal="BUY PE"

    if df['rsi'].iloc[-1]<40:
        score+=2

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
# 🚀 MAIN
# =========================================================
g=global_score()
n=news_score()

c1,c2,c3=st.columns(3)
c1.metric("🌍 Global", g)
c2.metric("📰 News", n)
c3.metric("⚠️ Risk", "HIGH" if n<-5 else "NORMAL")

# =========================================================
# 🏭 SECTOR PANEL (FIXED)
# =========================================================
st.subheader("🏭 Sector Strength")

sec_df=sector_strength()
st.dataframe(sec_df, use_container_width=True)

# Highlight best sector
best_sector=sec_df.iloc[0]
st.success(f"🔥 Strongest Sector: {best_sector['Sector']}")

# =========================================================
# 📊 STOCK ANALYSIS
# =========================================================
results=[]

for name,symbol in stocks.items():

    df=yf.download(symbol, period="3mo")
    if len(df)<30: continue

    df=clean(df)
    df=df[['Open','High','Low','Close','Volume']]
    df=indicators(df)

    s,signal=analyze(df)
    final=s+(g*0.2)+(n*0.2)

    price=df['Close'].iloc[-1]

    results.append({
        "Stock":name,
        "Score":round(final,2),
        "Signal":signal,
        "Price":round(price,2),
        "Target":round(price*1.03,2),
        "Stoploss":round(price*0.97,2)
    })

df_out=pd.DataFrame(results).sort_values(by="Score",ascending=False)

st.subheader("📈 Trade Opportunities")
st.dataframe(df_out, use_container_width=True)

# =========================================================
# 📊 CHART (FIXED - PLOTLY)
# =========================================================
best=df_out.iloc[0]
symbol=stocks[best['Stock']]

df=yf.download(symbol, period="3mo")
df=clean(df)

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close']
))

fig.update_layout(height=400, title=f"{best['Stock']} Chart")

st.plotly_chart(fig, use_container_width=True)

# =========================================================
# ⚠️ STRATEGY
# =========================================================
if n < -5:
    st.warning("📉 Risk-off: Prefer defensive stocks")
elif n > 5:
    st.success("🚀 Risk-on: Aggressive trades allowed")

st.caption("Auto-refresh every 5 min • Pro Intelligence")
