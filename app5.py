# =========================================================
# 📊 INDIAN MARKET INTELLIGENCE PRO V9 (WITH NEWS AI)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests

st.set_page_config(page_title="Market Intelligence PRO", layout="wide")

# =========================================================
# 🎨 UI
# =========================================================
st.markdown("""
<style>
body {background-color:#0b1220; color:#e5e7eb;}
h1,h2,h3 {color:white;}
.top-card {
    background: linear-gradient(135deg,#1d4ed8,#1e40af);
    padding:20px;
    border-radius:12px;
    color:white;
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Indian Market Intelligence PRO V9")

# =========================================================
# 🧼 CLEAN DF
# =========================================================
def clean_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# =========================================================
# 📈 FETCH DATA
# =========================================================
def fetch_data(symbol):
    df = yf.download(symbol, period="3mo", interval="1d")
    if df.empty:
        return df
    df = clean_df(df)
    df = df[['Open','High','Low','Close','Volume']].dropna()
    return df

# =========================================================
# 🌍 GLOBAL SCORE
# =========================================================
def global_score():
    indices = ["^GSPC","^IXIC","^DJI","^N225","^HSI"]
    score = 0

    for symbol in indices:
        df = yf.download(symbol, period="2d")
        if df.empty or len(df) < 2:
            continue

        df = clean_df(df)
        close = df['Close'].values

        score += 2 if close[-1] > close[-2] else -2

    return score

# =========================================================
# 📰 REAL NEWS FETCH
# =========================================================
def fetch_news():

    urls = [
        "https://newsapi.org/v2/top-headlines?category=business&language=en&pageSize=20&apiKey=2e99f73f7e4346c08f94c6d464bf7315",
        "https://newsapi.org/v2/everything?q=stock%20market%20india&language=en&pageSize=20&apiKey=YOUR_API_KEY"
    ]

    headlines = []

    for url in urls:
        try:
            r = requests.get(url)
            data = r.json()

            for article in data.get("articles", []):
                title = article.get("title", "")
                if title:
                    headlines.append(title.lower())
        except:
            continue

    return headlines

# =========================================================
# 🧠 NEWS INTELLIGENCE
# =========================================================
def news_score():

    headlines = fetch_news()

    negative = [
        "war","attack","conflict","tension","sanction",
        "inflation","rate hike","oil spike","crisis",
        "failed","collapse","fear","recession"
    ]

    positive = [
        "deal","agreement","growth","recovery",
        "rate cut","stimulus","positive","bullish"
    ]

    score = 0

    for h in headlines:

        for w in negative:
            if w in h:
                score -= 2

        for w in positive:
            if w in h:
                score += 2

    return score

# =========================================================
# 🏦 SECTOR SCORE
# =========================================================
def sector_score(symbol):
    sectors = {
        "BANK": ["HDFCBANK.NS","ICICIBANK.NS","SBIN.NS"],
        "IT": ["TCS.NS","INFY.NS"],
        "FMCG": ["ITC.NS"],
        "INFRA": ["LT.NS"],
        "CONSUMPTION": ["TITAN.NS"]
    }

    for sector, stocks in sectors.items():
        if symbol in stocks:
            score = 0
            for s in stocks:
                df = yf.download(s, period="2d")
                if df.empty or len(df) < 2:
                    continue
                df = clean_df(df)
                close = df['Close'].values
                score += 1 if close[-1] > close[-2] else -1
            return score

    return 0

# =========================================================
# 📊 INDICATORS
# =========================================================
def indicators(df):

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain/(loss+1e-9)
    rsi = 100-(100/(1+rs))

    df['stoch'] = ((rsi-rsi.rolling(14).min()) /
                   (rsi.rolling(14).max()-rsi.rolling(14).min()+1e-9))*100

    df['ema20'] = df['Close'].ewm(span=20).mean()
    df['ema_slope'] = df['ema20'].diff()

    return df

# =========================================================
# 🎯 STOCK SCORE
# =========================================================
def stock_score(df):

    s=0
    if df['stoch'].iloc[-1] > 70: s+=3
    if df['ema_slope'].iloc[-1] > 0: s+=3

    return s

# =========================================================
# 🚀 MAIN ENGINE
# =========================================================
stocks = {
"ITC":"ITC.NS",
"TCS":"TCS.NS",
"L&T":"LT.NS",
"ICICI":"ICICIBANK.NS",
"SBI":"SBIN.NS",
"HDFC":"HDFCBANK.NS",
"Titan":"TITAN.NS"
}

results=[]

g = global_score()
n = news_score()

# ⚠️ HIGH RISK ALERT
if n < -5:
    st.error("⚠️ High Risk Market - Avoid Aggressive Buying")

for name, symbol in stocks.items():

    df = fetch_data(symbol)
    if df.empty or len(df) < 30:
        continue

    df = indicators(df)

    s = stock_score(df)
    sec = sector_score(symbol)

    final = (s*0.4)+(sec*0.2)+(g*0.2)+(n*0.2)

    price = df['Close'].iloc[-1]
    target = price*(1+final/100)
    sl = price*0.97

    confidence = min(100,max(50,final*5))

    results.append({
        "Stock":name,
        "Score":round(final,2),
        "Confidence %":round(confidence,0),
        "Price":round(price,2),
        "Target":round(target,2),
        "Stoploss":round(sl,2)
    })

# =========================================================
# 📋 OUTPUT
# =========================================================
if results:

    df_out = pd.DataFrame(results).sort_values(by="Score", ascending=False)

    st.subheader("📈 Opportunities")
    st.dataframe(df_out, use_container_width=True)

    best = df_out.iloc[0]

    st.markdown(f"""
    <div class="top-card">
    🔥 Top Pick: {best['Stock']}<br><br>
    Confidence: {best['Confidence %']}%<br>
    Target: ₹{best['Target']}
    </div>
    """, unsafe_allow_html=True)

    st.write(f"🌍 Global Score: {g}")
    st.write(f"📰 News Score: {n}")

else:
    st.warning("No trades today")

st.caption("Real-time AI intelligence running...")
