import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pytz
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(page_title="MARKETSENSE PRO v6", page_icon="⚡", layout="wide")

# --- 2. HARDENED HIGH-CONTRAST CSS ---
st.markdown("""
    <style>
    /* Force high contrast for the main app */
    .stApp { background-color: #08090d !important; }
    
    /* Ensure all headers and text are bright white/silver */
    h1, h2, h3, p, span, .stMarkdown { color: #e4e8f5 !important; }
    
    /* Metrics High Visibility */
    [data-testid="stMetricValue"] { color: #00ffa3 !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #94a3b8 !important; text-transform: uppercase; font-size: 0.8rem !important; }

    /* Structural Anchors - Forced Visibility */
    .anchor-box { 
        background-color: #161b22 !important; 
        border: 1px solid #30363d !important;
        border-left: 5px solid #00ffa3 !important;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .anchor-title { color: #00ffa3 !important; font-weight: 800; font-size: 1rem; display: block; margin-bottom: 4px; }
    .anchor-desc { color: #cbd5e1 !important; font-size: 0.85rem; line-height: 1.4; }

    /* Stock Cards */
    .stock-card {
        background-color: #10131c !important;
        border: 1px solid #1e293b !important;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    .price-up { color: #00ffa3 !important; font-weight: bold; }
    .price-down { color: #ff4757 !important; font-weight: bold; }

    /* Horizontal Divider Visibility */
    hr { border: 0; border-top: 1px solid #30363d !important; margin: 20px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA ENGINE ---
SCAN_UNIVERSE = {
    "RELIANCE": {"name": "Reliance", "yf": "RELIANCE.NS"},
    "TCS": {"name": "TCS", "yf": "TCS.NS"},
    "HDFCBANK": {"name": "HDFC Bank", "yf": "HDFCBANK.NS"},
    "ICICIBANK": {"name": "ICICI Bank", "yf": "ICICIBANK.NS"},
    "HAL": {"name": "HAL", "yf": "HAL.NS"},
    "MM": {"name": "M&M", "yf": "M&M.NS"}
}

@st.cache_data(ttl=300)
def get_market_data():
    tickers = [v['yf'] for v in SCAN_UNIVERSE.values()]
    data = yf.download(tickers, period="5d", interval="1d", group_by='ticker', progress=False)
    results = {}
    for sym, info in SCAN_UNIVERSE.items():
        try:
            df = data[info['yf']] if len(tickers) > 1 else data
            ltp = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            chg = ((ltp - prev) / prev) * 100
            results[sym] = {"ltp": ltp, "chg": chg, "name": info['name']}
        except: continue
    return results

# --- 4. TOP INTERFACE ---
ist_now = datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%A, %b %d")

st.markdown(f"### 🏙️ MARKETSENSE PRO v6 | <span style='color:#7a84a0;'>{ist_now}</span>", unsafe_allow_html=True)

# Metrics Strip
m1, m2, m3, m4 = st.columns(4)
m1.metric("OMR / INR", "₹241.45", "0.08%")
m2.metric("NIFTY 50", "24,050.60", "1.02%")
m3.metric("GOLD 24K", "60.40", "-0.15%")
m4.metric("MARKET MOOD", "GREED", "54.92", delta_color="off")

st.markdown("---")

# --- 5. MAIN CONTENT ---
col_main, col_side = st.columns([8, 4])

with col_main:
    st.markdown("#### 🚀 Momentum Watchlist")
    market_data = get_market_data()
    
    # Render stock cards in a grid
    grid_cols = st.columns(3)
    for i, (sym, val) in enumerate(market_data.items()):
        color_class = "price-up" if val['chg'] >= 0 else "price-down"
        grid_cols[i % 3].markdown(f"""
            <div class="stock-card">
                <span style="color:#94a3b8; font-size:0.75rem; font-weight:bold;">{sym}</span><br>
                <span style="font-size:1.1rem; font-weight:800;">{val['name']}</span><hr style="margin:8px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.3rem; font-weight:bold;">₹{val['ltp']:,.2f}</span>
                    <span class="{color_class}">{val['chg']:.2f}%</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

with col_side:
    st.markdown("#### 🏛️ Structural Anchors")
    anchors = [
        ("Strait of Hormuz", "De-escalation allowing Brent to drop toward $85."),
        ("Nifty 24k Base", "Institutional floor confirmed at 23,800-24,000."),
        ("US-Iran Ceasefire", "Risk premium collapsing; bullish for EM equities."),
        ("Oman-India Corridor", "New trade protocols boosting logistics stocks.")
    ]
    
    for title, desc in anchors:
        st.markdown(f"""
            <div class="anchor-box">
                <span class="anchor-title">{title}</span>
                <span class="anchor-desc">{desc}</span>
            </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("<p style='text-align:center; color:#475569;'>Intelligence Terminal v6.0 | Secure Infrastructure</p>", unsafe_allow_html=True)
