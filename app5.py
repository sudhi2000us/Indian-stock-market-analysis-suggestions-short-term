# =========================================================
# 📊 INDIAN MARKET INTELLIGENCE PRO V8 (FULL SYSTEM)
# =========================================================

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

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

st.title("📊 Indian Market Intelligence PRO V8")

# =========================================================
# 📈 FETCH DATA
# =========================================================
def fetch_data(symbol):
    df = yf.download(symbol, period="3mo", interval="1d")

    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[['Open','High','Low','Close','Volume']].dropna()
    return df

# =========================================================
# 🌍 GLOBAL SCORE
# =========================================================
def global_score():
    indices = ["^GSPC","^IXIC","^DJI","^N225","^HSI"]
    score = 0

    for symbol in indices:
        df = yf.download(symbol, period="2d", interval="1d")

        if df.empty or len(df) < 2:
            continue

        # 🔧 FIX MULTI-INDEX ISSUE
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close'].astype(float).values

        if close[-1] > close[-2]:
            score += 2
        else:
            score -= 2

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
                if len(df) > 1:
                    if df['Close'].iloc[-1] > df['Close'].iloc[-2]:
                        score += 1
                    else:
                        score -= 1
            return score
    return 0

# =========================================================
# 🧠 INDICATORS
# =========================================================
def indicators(df):

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain/(loss+1e-9)
    rsi = 100-(100/(1+rs))

    df['stoch_rsi'] = ((rsi-rsi.rolling(14).min()) /
                       (rsi.rolling(14).max()-rsi.rolling(14).min()+1e-9))*100

    hh = df['High'].rolling(14).max()
    ll = df['Low'].rolling(14).min()
    df['williams'] = -100*((hh-df['Close'])/(hh-ll+1e-9))

    close = df['Close'].values
    vol = df['Volume'].values
    obv=[0]
    for i in range(1,len(close)):
        if close[i]>close[i-1]: obv.append(obv[-1]+vol[i])
        elif close[i]<close[i-1]: obv.append(obv[-1]-vol[i])
        else: obv.append(obv[-1])
    df['obv']=obv
    df['obv_slope']=pd.Series(obv).diff()

    vwap=(df['Close']*df['Volume']).cumsum()/df['Volume'].cumsum()
    df['vwap_dev']=(df['Close']-vwap)/vwap

    dc_high=df['High'].rolling(20).max()
    dc_low=df['Low'].rolling(20).min()
    df['donchian']=((df['Close']-dc_low)/(dc_high-dc_low+1e-9))*100

    df['ema20']=df['Close'].ewm(span=20).mean()
    df['ema_slope']=df['ema20'].diff()

    return df

# =========================================================
# 🎯 STOCK SCORE
# =========================================================
def stock_score(df):

    s=0

    if df['stoch_rsi'].iloc[-1]>70: s+=3
    if df['williams'].iloc[-1]<-80: s+=3
    if df['obv_slope'].iloc[-1]>0: s+=4
    if df['vwap_dev'].iloc[-1]<-0.01: s+=2
    if df['donchian'].iloc[-1]>70: s+=3
    if df['ema_slope'].iloc[-1]>0: s+=3

    return s

# =========================================================
# 📊 STOCK LIST
# =========================================================
stocks={
"ITC":"ITC.NS",
"TCS":"TCS.NS",
"L&T":"LT.NS",
"ICICI":"ICICIBANK.NS",
"SBI":"SBIN.NS",
"HDFC":"HDFCBANK.NS",
"Titan":"TITAN.NS",
"Infosys":"INFY.NS",
"Reliance":"RELIANCE.NS"
}

results=[]

g_score=global_score()

# =========================================================
# 🚀 MAIN ENGINE
# =========================================================
for name,symbol in stocks.items():

    df=fetch_data(symbol)

    if df.empty or len(df)<30:
        continue

    df=indicators(df)

    s_score=stock_score(df)
    sec_score=sector_score(symbol)

    final=(s_score*0.5)+(sec_score*0.2)+(g_score*0.3)

    price=df['Close'].iloc[-1]

    target=price*(1+final/100)
    sl=price*0.97

    confidence=min(100,max(50,final*5))

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

    df_out=pd.DataFrame(results).sort_values(by="Score",ascending=False)

    st.subheader("📈 Short Term Opportunities (1W - 1M)")
    st.dataframe(df_out,use_container_width=True)

    best=df_out.iloc[0]

    st.markdown(f"""
    <div class="top-card">
    🔥 <b>Top Pick: {best['Stock']}</b><br><br>
    Score: {best['Score']}<br>
    Confidence: {best['Confidence %']}%<br>
    Price: ₹{best['Price']}<br>
    Target: ₹{best['Target']}<br>
    Stoploss: ₹{best['Stoploss']}
    </div>
    """,unsafe_allow_html=True)

    # Market bias
    if g_score>5:
        st.success("📈 Market Bias: Bullish")
    elif g_score<-5:
        st.error("📉 Market Bias: Bearish")
    else:
        st.warning("⚖️ Market Bias: Neutral")

else:
    st.warning("No opportunities today")

st.caption("AI-driven multi-layer intelligence running...")
