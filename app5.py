import math
import sqlite3
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf
import pytz
from datetime import datetime, time, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from streamlit_autorefresh import st_autorefresh

# ============================================================
# CONFIG & THEME
# ============================================================
st.set_page_config(page_title="MARKETSENSE PRO v6", page_icon="⚡", layout="wide")
st_autorefresh(interval=900000, key="ms6_refresh")
IST = pytz.timezone("Asia/Kolkata")

# Custom CSS for the "Intelligence" Look
st.markdown("""
<style>
    .main { background-color: #08090d !important; color: #e4e8f5; }
    .stMetric { background: #10131c; padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); }
    .anchor-item { 
        background: #10131c !important; color: #e4e8f5 !important; 
        padding: 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
        border-left: 5px solid #00ffa3; margin-bottom: 10px;
    }
    .anchor-title { font-weight: 800; color: #00ffa3; display: block; }
    .anchor-desc { color: #7a84a0 !important; font-size: 0.85rem; }
    .buy-card { border-top: 3px solid #00ffa3; background: #10131c; padding: 15px; border-radius: 10px; }
    .sell-card { border-top: 3px solid #ff4757; background: #10131c; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# UNIVERSE & DATA ENGINES
# ============================================================
SCAN_UNIVERSE = {
    "RELIANCE": {"name": "Reliance", "yf": "RELIANCE.NS"},
    "TCS": {"name": "TCS", "yf": "TCS.NS"},
    "HDFCBANK": {"name": "HDFC Bank", "yf": "HDFCBANK.NS"},
    "ICICIBANK": {"name": "ICICI Bank", "yf": "ICICIBANK.NS"},
    "HAL": {"name": "HAL", "yf": "HAL.NS"},
    "MM": {"name": "M&M", "yf": "M&M.NS"},
    "DIXON": {"name": "Dixon", "yf": "DIXON.NS"},
    "SUZLON": {"name": "Suzlon", "yf": "SUZLON.NS"}
}

def clean_ohlcv(df):
    """Handles YFinance MultiIndex columns and cleans data."""
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=['Close'])

# ── Technical Indicators ────────────────────────────────────
def enrich_data(df):
    if len(df) < 50: return pd.DataFrame()
    df = df.copy()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # EMAs & Trends
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['Signal'] = np.where(df['EMA20'] > df['EMA50'], "BUY", "WATCH")
    
    # Volatility / Squeeze
    df['STD'] = df['Close'].rolling(20).std()
    df['Upper'] = df['EMA20'] + (df['STD'] * 2)
    df['Lower'] = df['EMA20'] - (df['STD'] * 2)
    df['Squeeze'] = (df['Upper'] - df['Lower']) / df['EMA20']
    
    return df

# ============================================================
# DATA FETCHING (PARALLEL)
# ============================================================
@st.cache_data(ttl=300)
def fetch_all_data():
    results = {}
    tickers = [v['yf'] for v in SCAN_UNIVERSE.values()]
    
    # Fetch data in one go for efficiency
    raw_data = yf.download(tickers, period="1y", interval="1d", group_by='ticker', progress=False)
    
    for symbol, info in SCAN_UNIVERSE.items():
        try:
            ticker_df = raw_data[info['yf']] if len(tickers) > 1 else raw_data
            df = clean_ohlcv(ticker_df)
            df = enrich_data(df)
            if not df.empty:
                results[symbol] = {
                    "ltp": df['Close'].iloc[-1],
                    "change": ((df['Close'].iloc[-1] / df['Close'].iloc[-2]) - 1) * 100,
                    "rsi": df['RSI'].iloc[-1],
                    "signal": df['Signal'].iloc[-1],
                    "df": df
                }
        except: continue
    return results

# ============================================================
# MAIN INTERFACE
# ============================================================
def main():
    # Top Metrics Strip
    data = fetch_all_data()
    
    st.markdown('<h1 style="font-family:Syne; letter-spacing:-2px;">⚡ MARKETSENSE PRO v6</h1>', unsafe_allow_html=True)
    
    # 1. Dashboard Summary
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("OMR / INR", "₹241.45", "0.12%")
    with m2: st.metric("Gold 24K", "60.40", "-0.5%")
    with m3: st.metric("NIFTY 50", "24,050", "1.02%")
    with m4: st.metric("Market Mood", "GREED", "54.92", delta_color="off")

    st.divider()

    # 2. Main Strategy Layout
    col_left, col_right = st.columns([8, 4])
    
    with col_left:
        st.subheader("🚀 High Conviction Radar")
        grid = st.columns(3)
        for i, (sym, val) in enumerate(data.items()):
            with grid[i % 3]:
                card_class = "buy-card" if val['signal'] == "BUY" else "sell-card"
                st.markdown(f"""
                    <div class="{card_class}">
                        <h3 style="margin:0;">{sym}</h3>
                        <p style="color:#7a84a0; font-size:0.8rem; margin-bottom:10px;">{SCAN_UNIVERSE[sym]['name']}</p>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="font-size:1.2rem; font-weight:bold;">₹{val['ltp']:.2f}</span>
                            <span style="color:{'#00ffa3' if val['change'] > 0 else '#ff4757'}">{val['change']:.2f}%</span>
                        </div>
                        <div style="margin-top:10px; font-size:0.8rem;">
                            RSI: <b>{val['rsi']:.1f}</b> | Signal: <b style="color:{'#00ffa3' if val['signal'] == 'BUY' else '#ffd166'}">{val['signal']}</b>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                st.write("")

    with col_right:
        st.subheader("🏛️ Structural Anchors")
        anchors = [
            ("Strait of Hormuz", "De-escalation allowing Brent to drop toward $85."),
            ("Nifty 24k Base", "Strong institutional floor confirmed on Friday."),
            ("US-Iran Ceasefire", "Risk premium collapsing; bullish for EM equities."),
            ("FII Neutrality", "Selling pressure reaching exhaustion levels.")
        ]
        for title, desc in anchors:
            st.markdown(f"""
                <div class="anchor-item">
                    <span class="anchor-title">{title}</span>
                    <span class="anchor-desc">{desc}</span>
                </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
