# ═══════════════════════════════════════════════════════════════════
#  MARKETSENSE PRO v7  — Indian Short-Term Trading Intelligence
#  Real data · News sentiment · Technical scoring · Auto-refresh 5min
# ═══════════════════════════════════════════════════════════════════

import re
import math
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh

# ──────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MARKETSENSE PRO",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Auto-refresh every 5 minutes
st_autorefresh(interval=300_000, key="ms7_refresh")

IST = ZoneInfo("Asia/Kolkata")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# ──────────────────────────────────────────────────────────────────
# STOCK UNIVERSE  (short-term focused — high liquidity, active F&O)
# ──────────────────────────────────────────────────────────────────
UNIVERSE = {
    # Banking
    "HDFCBANK":   {"name": "HDFC Bank",          "sector": "Banking",        "yf": "HDFCBANK.NS"},
    "ICICIBANK":  {"name": "ICICI Bank",          "sector": "Banking",        "yf": "ICICIBANK.NS"},
    "SBIN":       {"name": "SBI",                 "sector": "Banking",        "yf": "SBIN.NS"},
    "AXISBANK":   {"name": "Axis Bank",           "sector": "Banking",        "yf": "AXISBANK.NS"},
    "KOTAKBANK":  {"name": "Kotak Bank",          "sector": "Banking",        "yf": "KOTAKBANK.NS"},
    # IT
    "TCS":        {"name": "TCS",                 "sector": "IT",             "yf": "TCS.NS"},
    "INFY":       {"name": "Infosys",             "sector": "IT",             "yf": "INFY.NS"},
    "HCLTECH":    {"name": "HCL Tech",            "sector": "IT",             "yf": "HCLTECH.NS"},
    "WIPRO":      {"name": "Wipro",               "sector": "IT",             "yf": "WIPRO.NS"},
    "TECHM":      {"name": "Tech Mahindra",       "sector": "IT",             "yf": "TECHM.NS"},
    # Energy
    "RELIANCE":   {"name": "Reliance",            "sector": "Energy",         "yf": "RELIANCE.NS"},
    "NTPC":       {"name": "NTPC",                "sector": "Energy",         "yf": "NTPC.NS"},
    "TATAPOWER":  {"name": "Tata Power",          "sector": "Energy",         "yf": "TATAPOWER.NS"},
    "COALINDIA":  {"name": "Coal India",          "sector": "Energy",         "yf": "COALINDIA.NS"},
    # Auto
    "TATAMOTORS": {"name": "Tata Motors",         "sector": "Auto",           "yf": "TATAMOTORS.NS"},
    "MARUTI":     {"name": "Maruti Suzuki",       "sector": "Auto",           "yf": "MARUTI.NS"},
    "MM":         {"name": "M&M",                 "sector": "Auto",           "yf": "M&M.NS"},
    "EICHERMOT":  {"name": "Eicher Motors",       "sector": "Auto",           "yf": "EICHERMOT.NS"},
    # Defence
    "HAL":        {"name": "HAL",                 "sector": "Defence",        "yf": "HAL.NS"},
    "BEL":        {"name": "BEL",                 "sector": "Defence",        "yf": "BEL.NS"},
    "MAZDOCK":    {"name": "Mazagon Dock",        "sector": "Defence",        "yf": "MAZDOCK.NS"},
    # Infra
    "LT":         {"name": "L&T",                 "sector": "Infra",          "yf": "LT.NS"},
    "RVNL":       {"name": "RVNL",                "sector": "Infra",          "yf": "RVNL.NS"},
    "POWERGRID":  {"name": "Power Grid",          "sector": "Infra",          "yf": "POWERGRID.NS"},
    # Metals
    "TATASTEEL":  {"name": "Tata Steel",          "sector": "Metals",         "yf": "TATASTEEL.NS"},
    "JSWSTEEL":   {"name": "JSW Steel",           "sector": "Metals",         "yf": "JSWSTEEL.NS"},
    # Consumer
    "ITC":        {"name": "ITC",                 "sector": "Consumer",       "yf": "ITC.NS"},
    "TITAN":      {"name": "Titan",               "sector": "Consumer",       "yf": "TITAN.NS"},
    "HINDUNILVR": {"name": "HUL",                 "sector": "Consumer",       "yf": "HINDUNILVR.NS"},
    # NBFC
    "BAJFINANCE": {"name": "Bajaj Finance",       "sector": "NBFC",           "yf": "BAJFINANCE.NS"},
    "BAJAJFINSV": {"name": "Bajaj Finserv",       "sector": "NBFC",           "yf": "BAJAJFINSV.NS"},
    # Pharma
    "SUNPHARMA":  {"name": "Sun Pharma",          "sector": "Pharma",         "yf": "SUNPHARMA.NS"},
    # Telecom
    "BHARTIARTL": {"name": "Bharti Airtel",       "sector": "Telecom",        "yf": "BHARTIARTL.NS"},
    # Realty
    "GODREJPROP": {"name": "Godrej Prop",         "sector": "Realty",         "yf": "GODREJPROP.NS"},
    # Mfg
    "DIXON":      {"name": "Dixon Tech",          "sector": "Mfg",            "yf": "DIXON.NS"},
}

GLOBAL_MAP = {
    "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "NIKKEI": "^N225",
    "HANG SENG": "^HSI", "BRENT": "BZ=F", "GOLD": "GC=F", "USD/INR": "INR=X",
}

SECTOR_KW = {
    "Banking":  ["rbi","repo","bank","credit","rupee","npa","liquidity","rate cut","rate hike"],
    "IT":       ["ai","tech","cloud","software","nasdaq","digital","dollar","it spending","visa"],
    "Energy":   ["oil","crude","brent","opec","gas","energy","petrol","refinery"],
    "Auto":     ["auto","vehicle","ev","electric","tractor","sales","two-wheeler","car"],
    "Defence":  ["defence","military","war","border","drdo","weapons","army","navy"],
    "Infra":    ["capex","infrastructure","rail","road","construction","metro","nhpc"],
    "Metals":   ["steel","metal","iron ore","copper","aluminium","commodity","china"],
    "Consumer": ["inflation","consumption","fmcg","gst","demand","retail","festive"],
    "NBFC":     ["credit","loan","finance","nbfc","housing","microfinance"],
    "Pharma":   ["pharma","drug","fda","usfda","api","biotech","healthcare"],
    "Telecom":  ["telecom","5g","spectrum","airtel","jio"],
    "Realty":   ["real estate","housing","property","reit","residential"],
    "Mfg":      ["manufacturing","pli","electronics","semiconductor","make in india"],
}

POS_WORDS = {
    "rally","surge","breakout","beats","growth","strong","recover","upgrade","win",
    "record high","all-time high","outperform","rate cut","stimulus","approval",
    "inflow","ceasefire","fall in oil","order win","boost","expansion","positive",
    "bullish","momentum","accelerating","beat","robust","solid","guidance raised",
}
NEG_WORDS = {
    "crash","selloff","fall","war","tariff","sanction","downgrade","weak","default",
    "probe","ban","concern","outflow","inflation spike","oil spike","rate hike",
    "profit warning","recession","slowdown","escalation","conflict","misses","cuts",
    "fragile","panic","collapse","volatile","uncertainty","disappointed",
}

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
NSE_HOME  = "https://www.nseindia.com/"

# ──────────────────────────────────────────────────────────────────
# PREMIUM CSS
# ──────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">

<style>
/* ── ROOT TOKENS ── */
:root{
  --bg:#070810; --surface:#0d0f1a; --card:#111422; --card2:#151829;
  --border:rgba(255,255,255,0.06); --border2:rgba(255,255,255,0.12);
  --text:#dde3f5; --muted:#636d8a; --muted2:#3a4260;
  --green:#0dffb0; --green-dim:rgba(13,255,176,0.12);
  --red:#ff3d5a;   --red-dim:rgba(255,61,90,0.12);
  --amber:#ffb740; --amber-dim:rgba(255,183,64,0.12);
  --blue:#3d9eff;  --blue-dim:rgba(61,158,255,0.12);
  --purple:#b57bff;--purple-dim:rgba(181,123,255,0.12);
  --cyan:#00d4ff;
  --glow-g:0 0 24px rgba(13,255,176,0.2);
  --glow-r:0 0 24px rgba(255,61,90,0.2);
  --shadow:0 24px 64px rgba(0,0,0,0.7);
}

/* ── GLOBAL ── */
html,body,.stApp{background:var(--bg)!important;font-family:'Outfit',sans-serif;}
.block-container{max-width:1440px!important;padding:0 1.2rem 3rem!important;}
*{box-sizing:border-box;}
h1,h2,h3,h4,h5,h6,p,span,div,label,li{color:var(--text);}
a{color:var(--blue);text-decoration:none;}a:hover{opacity:.8;}

/* hide streamlit chrome */
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden!important;}
[data-testid="stSidebar"]{display:none!important;}

/* ── TOPBAR ── */
.topbar{
  display:flex;align-items:center;justify-content:space-between;
  padding:14px 20px;margin-bottom:14px;
  background:linear-gradient(135deg,rgba(13,15,26,0.95),rgba(17,20,34,0.95));
  border:1px solid var(--border);border-radius:16px;
  backdrop-filter:blur(20px);
  position:sticky;top:0;z-index:100;
}
.logo{
  font-family:'Bebas Neue',sans-serif;letter-spacing:.1em;font-size:1.7rem;
  background:linear-gradient(110deg,var(--green) 0%,var(--cyan) 50%,var(--blue) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}
.logo-sub{font-family:'JetBrains Mono',monospace;font-size:.6rem;color:var(--muted);letter-spacing:.15em;display:block;margin-top:-4px;}
.topbar-pills{display:flex;gap:7px;flex-wrap:wrap;}
.topbar-time{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--muted);text-align:right;line-height:1.8;}
.topbar-time b{color:var(--text);}

/* ── PILL BADGES ── */
.pill{display:inline-flex;align-items:center;gap:5px;padding:.26rem .7rem;border-radius:999px;
  font-family:'JetBrains Mono',monospace;font-size:.66rem;font-weight:700;
  letter-spacing:.05em;border:1px solid;text-transform:uppercase;}
.pill::before{content:'●';font-size:.42rem;}
.pg{background:rgba(13,255,176,.1);color:var(--green);border-color:rgba(13,255,176,.25);}
.pr{background:rgba(255,61,90,.1);color:var(--red);border-color:rgba(255,61,90,.25);}
.pa{background:rgba(255,183,64,.1);color:var(--amber);border-color:rgba(255,183,64,.25);}
.pb{background:rgba(61,158,255,.1);color:var(--blue);border-color:rgba(61,158,255,.25);}
.pp{background:rgba(181,123,255,.1);color:var(--purple);border-color:rgba(181,123,255,.25);}

/* ── TICKER TAPE ── */
.ticker-wrap{overflow:hidden;background:rgba(13,15,26,.9);border:1px solid var(--border);
  border-radius:10px;padding:8px 0;margin-bottom:12px;}
.ticker-inner{display:flex;gap:32px;white-space:nowrap;animation:scroll 40s linear infinite;}
.ticker-inner:hover{animation-play-state:paused;}
@keyframes scroll{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}
.t-item{font-family:'JetBrains Mono',monospace;font-size:.72rem;display:inline-flex;align-items:center;gap:8px;}
.t-sym{color:var(--muted);letter-spacing:.06em;}
.t-price{color:var(--text);font-weight:600;}
.t-chg-up{color:var(--green);}
.t-chg-dn{color:var(--red);}

/* ── STAT STRIP ── */
.stat-strip{display:grid;grid-template-columns:repeat(7,1fr);gap:9px;margin-bottom:12px;}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:13px 15px;position:relative;overflow:hidden;}
.stat::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.stat.sg::before{background:linear-gradient(90deg,var(--green),transparent);}
.stat.sr::before{background:linear-gradient(90deg,var(--red),transparent);}
.stat.sa::before{background:linear-gradient(90deg,var(--amber),transparent);}
.stat.sb::before{background:linear-gradient(90deg,var(--blue),transparent);}
.stat.sp::before{background:linear-gradient(90deg,var(--purple),transparent);}
.stat-lbl{font-family:'JetBrains Mono',monospace;font-size:.58rem;color:var(--muted);
  text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;}
.stat-val{font-family:'Bebas Neue',sans-serif;font-size:1.55rem;color:#fff;letter-spacing:.03em;line-height:1;}
.stat-sub{font-size:.73rem;margin-top:4px;}
.sup{color:var(--green);} .sdn{color:var(--red);} .sneu{color:var(--muted);}

/* ── SECTION HEADER ── */
.sec{font-family:'Bebas Neue',sans-serif;font-size:1.15rem;letter-spacing:.08em;
  color:#fff;display:flex;align-items:center;gap:10px;margin:18px 0 11px;}
.sec::before{content:'';width:3px;height:18px;border-radius:2px;
  background:linear-gradient(180deg,var(--green),var(--blue));flex-shrink:0;}

/* ── TRADE CARDS ── */
.trade-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;}
.trade-card{
  background:var(--card);border:1px solid var(--border);border-radius:16px;
  padding:18px;position:relative;overflow:hidden;
  transition:transform .18s,border-color .18s,box-shadow .18s;
}
.trade-card:hover{transform:translateY(-3px);border-color:var(--border2);box-shadow:var(--shadow);}
.trade-card.buy::before,.trade-card.watch::before,.trade-card.avoid::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.trade-card.buy::before{background:linear-gradient(90deg,var(--green),var(--cyan));}
.trade-card.watch::before{background:linear-gradient(90deg,var(--amber),var(--blue));}
.trade-card.avoid::before{background:linear-gradient(90deg,var(--red),transparent);}
.tc-sym{font-family:'JetBrains Mono',monospace;font-size:.65rem;color:var(--muted);letter-spacing:.12em;}
.tc-name{font-family:'Outfit',sans-serif;font-size:1rem;font-weight:800;color:#fff;margin:2px 0;}
.tc-sector{font-size:.72rem;color:var(--muted);margin-bottom:10px;}
.tc-signal{font-family:'JetBrains Mono',monospace;font-size:.88rem;font-weight:700;margin-bottom:2px;}
.tc-signal.buy{color:var(--green);} .tc-signal.watch{color:var(--amber);} .tc-signal.avoid{color:var(--red);}
.tc-setup{display:inline-block;padding:2px 9px;border-radius:999px;font-size:.65rem;
  font-weight:700;background:rgba(255,255,255,.06);color:var(--muted);margin-bottom:10px;}
.tc-bar{height:3px;border-radius:999px;background:rgba(255,255,255,.07);overflow:hidden;margin-bottom:9px;}
.tc-bar-fill{height:100%;border-radius:999px;}
.tcbg{background:linear-gradient(90deg,#00c97a,var(--green));}
.tcba{background:linear-gradient(90deg,#e6920a,var(--amber));}
.tcbr{background:linear-gradient(90deg,#cc1133,var(--red));}
.tc-row{display:flex;justify-content:space-between;font-size:.79rem;
  padding:3px 0;border-bottom:1px solid rgba(255,255,255,.04);}
.tc-row .k{color:var(--muted);}
.tc-row .v{color:#fff;font-weight:600;}
.v-up{color:var(--green)!important;} .v-dn{color:var(--red)!important;}
.tc-why{margin-top:9px;font-size:.72rem;color:var(--muted);line-height:1.5;
  border-top:1px solid rgba(255,255,255,.05);padding-top:8px;}
.tc-score{display:flex;align-items:center;gap:10px;margin-bottom:6px;}
.score-ring{width:42px;height:42px;border-radius:50%;display:flex;
  align-items:center;justify-content:center;position:relative;}
.score-ring-inner{position:absolute;inset:5px;background:var(--card);border-radius:50%;}
.score-ring-val{position:relative;z-index:1;font-family:'JetBrains Mono',monospace;
  font-size:.68rem;font-weight:700;color:#fff;}

/* ── NEWS CARDS ── */
.news-feed{display:flex;flex-direction:column;gap:6px;}
.news-item{display:flex;gap:12px;align-items:flex-start;padding:10px 12px;
  background:var(--card);border:1px solid var(--border);border-radius:10px;
  transition:border-color .15s;}
.news-item:hover{border-color:var(--border2);}
.ns{min-width:28px;height:28px;border-radius:7px;display:flex;align-items:center;
  justify-content:center;font-family:'JetBrains Mono',monospace;font-size:.68rem;font-weight:700;}
.ns-p{background:var(--green-dim);color:var(--green);}
.ns-n{background:var(--red-dim);color:var(--red);}
.ns-0{background:rgba(255,255,255,.05);color:var(--muted);}
.nt{font-size:.83rem;color:var(--text);line-height:1.4;}
.nt a{color:var(--text);}
.nm{font-size:.69rem;color:var(--muted2);margin-top:3px;}
.ns-imp{padding:2px 7px;border-radius:4px;font-size:.63rem;font-weight:700;margin-left:6px;}
.ns-imp.high{background:var(--red-dim);color:var(--red);}
.ns-imp.med{background:var(--amber-dim);color:var(--amber);}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# TECHNICAL INDICATORS
# ──────────────────────────────────────────────────────────────────
def safe(v, d=np.nan):
    try: return float(v)
    except: return d

def pct(cur, prev):
    if prev in [0, None] or pd.isna(prev) or pd.isna(cur): return np.nan
    return ((cur / prev) - 1) * 100

def clean_df(df):
    if df is None or df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        lv = df.columns.get_level_values
        if len(set(lv(0))) == 1: df.columns = lv(1)
        elif len(set(lv(1))) == 1: df.columns = lv(0)
    cols = [c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
    return df[cols].copy().dropna(subset=["Close"])

def rsi_calc(s, p=14):
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    al = l.ewm(alpha=1/p, min_periods=p, adjust=False).mean()
    return 100 - (100 / (1 + ag / al.replace(0, np.nan)))

def macd_calc(s, f=12, sl=26, sig=9):
    ef = s.ewm(span=f, adjust=False).mean()
    es = s.ewm(span=sl, adjust=False).mean()
    line = ef - es
    signal = line.ewm(span=sig, adjust=False).mean()
    return line, signal, line - signal

def atr_calc(df, p=14):
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(p).mean()

def stoch_rsi(s, p=14, k=3):
    r = rsi_calc(s, p)
    mn = r.rolling(p).min(); mx = r.rolling(p).max()
    return ((r - mn) / (mx - mn + 1e-9) * 100).rolling(k).mean()

def obv_calc(df):
    return (np.sign(df["Close"].diff()).fillna(0) * df["Volume"]).cumsum()

def bb_calc(s, p=20, std=2):
    mid = s.rolling(p).mean(); sd = s.rolling(p).std()
    return mid + std*sd, mid, mid - std*sd

def enrich(df):
    if df is None or df.empty or len(df) < 60: return pd.DataFrame()
    x = df.copy()
    for sp in [9, 20, 50, 100, 200]:
        x[f"EMA{sp}"] = x["Close"].ewm(span=sp, adjust=False).mean()
    x["RSI14"]    = rsi_calc(x["Close"], 14)
    x["StochRSI"] = stoch_rsi(x["Close"])
    x["ATR14"]    = atr_calc(x, 14)
    x["OBV"]      = obv_calc(x)
    x["OBV_EMA"]  = x["OBV"].ewm(span=20, adjust=False).mean()
    x["VOL20"]    = x["Volume"].rolling(20).mean()
    x["VOL_R"]    = x["Volume"] / x["VOL20"]
    x["HH20"]     = x["High"].rolling(20).max()
    x["LL20"]     = x["Low"].rolling(20).min()
    x["HH50"]     = x["High"].rolling(50).max()
    x["DONCH"]    = ((x["Close"] - x["LL20"]) / (x["HH20"] - x["LL20"] + 1e-9)) * 100
    x["BB_U"], x["BB_M"], x["BB_L"] = bb_calc(x["Close"])
    x["BB_W"]     = (x["BB_U"] - x["BB_L"]) / x["BB_M"] * 100
    x["BB_W_AVG"] = x["BB_W"].rolling(50).mean()
    ml, ms, mh    = macd_calc(x["Close"])
    x["MACD"], x["MACD_S"], x["MACD_H"] = ml, ms, mh
    x["EMA_SLOPE"] = x["EMA20"].diff(3) / x["Close"] * 100
    x["52W_H"]    = x["High"].rolling(252).max()
    x["52W_L"]    = x["Low"].rolling(252).min()
    x["52W_PCT"]  = ((x["Close"] - x["52W_L"]) / (x["52W_H"] - x["52W_L"] + 1e-9)) * 100
    for p_ in [1, 3, 5, 10, 20, 60]:
        x[f"RET{p_}"] = x["Close"].pct_change(p_)
    return x.dropna()

def setup_label(d):
    c=safe(d.get("Close")); hh20=safe(d.get("HH20")); ema20=safe(d.get("EMA20"))
    ema50=safe(d.get("EMA50")); rsi=safe(d.get("RSI14")); sr=safe(d.get("StochRSI"))
    vr=safe(d.get("VOL_R"),1); donch=safe(d.get("DONCH",50))
    bw=safe(d.get("BB_W",5)); bwa=safe(d.get("BB_W_AVG",5))
    if bw < bwa * 0.80 and rsi > 48: return "BB Squeeze 🔥"
    if c >= 0.99*hh20 and rsi >= 58 and vr >= 1.4: return "Vol Breakout 🚀"
    if c >= 0.99*hh20 and rsi >= 56: return "Breakout"
    if donch >= 85 and rsi >= 63: return "Momentum"
    if c > ema20 > ema50 and sr <= 40: return "EMA Pullback"
    if c >= ema50 and rsi <= 48 and sr <= 28: return "Bounce"
    if c > ema20 and sr <= 18: return "StochRSI Reset"
    return "Trend"

# ──────────────────────────────────────────────────────────────────
# DATA FETCHING
# ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_price(yf_sym, period="1y", interval="1d"):
    try:
        df = yf.download(yf_sym, period=period, interval=interval,
                         auto_adjust=True, progress=False, threads=False)
        return clean_df(df)
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_quote(yf_sym):
    df = fetch_price(yf_sym, period="5d")
    if df.empty or len(df) < 2: return {}
    last = safe(df["Close"].iloc[-1]); prev = safe(df["Close"].iloc[-2])
    hi = safe(df["High"].iloc[-1]); lo = safe(df["Low"].iloc[-1])
    vol = safe(df["Volume"].iloc[-1])
    return {"last": last, "prev": prev, "chg": pct(last, prev),
            "high": hi, "low": lo, "volume": vol}

def parallel_prices(universe):
    """Fetch all stock histories in parallel."""
    out = {}
    def _f(sym, yf_sym):
        return sym, fetch_price(yf_sym, period="1y")
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(_f, sym, info["yf"]): sym for sym, info in universe.items()}
        for f in as_completed(futs):
            sym, df = f.result()
            out[sym] = df
    return out

def parallel_quotes(universe):
    """Fetch all live quotes in parallel."""
    out = {}
    def _f(sym, yf_sym):
        return sym, fetch_quote(yf_sym)
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(_f, sym, info["yf"]): sym for sym, info in universe.items()}
        for f in as_completed(futs):
            sym, q = f.result()
            out[sym] = q
    return out

@st.cache_data(ttl=300)
def fetch_global():
    out = {}
    def _f(name, ticker):
        return name, fetch_quote(ticker)
    with ThreadPoolExecutor(max_workers=7) as ex:
        futs = {ex.submit(_f, name, ticker): name for name, ticker in GLOBAL_MAP.items()}
        for f in as_completed(futs):
            name, q = f.result()
            out[name] = q
    return out

@st.cache_data(ttl=600)
def fetch_news_gdelt(query, n=15):
    items = []
    try:
        r = requests.get(GDELT_URL, params={
            "query": query, "mode": "ArtList", "maxrecords": n,
            "format": "json", "sort": "DateDesc"
        }, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for a in r.json().get("articles", []):
            t = a.get("title","").strip(); l = a.get("url","").strip()
            if t and l:
                items.append({"title":t,"link":l,"source":a.get("domain",""),"date":a.get("seendate","")})
    except: pass
    return items

@st.cache_data(ttl=600)
def fetch_rss(url, source):
    items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15); r.raise_for_status()
        root = ET.fromstring(r.text)
        for item in root.findall(".//item")[:12]:
            t = item.findtext("title","").strip(); l = item.findtext("link","").strip()
            if t and l:
                items.append({"title":t,"link":l,"source":source,"date":item.findtext("pubDate","")})
    except: pass
    return items

@st.cache_data(ttl=600)
def collect_all_news():
    rows = []
    queries = {
        "macro":   '"Nifty" OR "Sensex" OR RBI OR rupee OR inflation OR tariffs OR "Indian market"',
        "global":  '"Wall Street" OR "Fed" OR oil OR crude OR "US economy" OR bonds',
        "geopolit":'Trump OR China OR "Middle East" OR oil OR sanctions OR "trade war"',
    }
    for bucket, q in queries.items():
        for item in fetch_gdelt_news_inner(q, 12):
            rows.append({**item, "bucket": bucket, "score": news_score(item["title"])})

    for item in fetch_rss("https://www.pib.gov.in/rssMain.aspx?reg=3&lang=1", "PIB"):
        rows.append({**item, "bucket": "india_policy", "score": news_score(item["title"])})

    if not rows:
        return pd.DataFrame(columns=["title","link","source","date","bucket","score"])
    df = pd.DataFrame(rows).drop_duplicates(subset=["title","link"])
    df["sector_impact"] = df["title"].apply(sector_tags)
    df["importance"] = df["score"].abs() + df["title"].str.len().apply(lambda x: 1 if x > 60 else 0)
    return df.sort_values("importance", ascending=False)

def fetch_gdelt_news_inner(query, n):
    items = []
    try:
        r = requests.get(GDELT_URL, params={
            "query": query, "mode": "ArtList", "maxrecords": n,
            "format": "json", "sort": "DateDesc"
        }, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for a in r.json().get("articles", []):
            t = a.get("title","").strip(); l = a.get("url","").strip()
            if t and l:
                items.append({"title":t,"link":l,"source":a.get("domain",""),"date":a.get("seendate","")})
    except: pass
    return items

def news_score(text):
    t = text.lower(); s = 0
    for w in POS_WORDS:
        if w in t: s += 1
    for w in NEG_WORDS:
        if w in t: s -= 1
    if ("oil" in t or "crude" in t):
        if any(w in t for w in ["spike","surges","jumps sharply"]): s -= 2
        if any(w in t for w in ["falls","drops","eases","cools"]): s += 1
    if "ceasefire" in t: s += 2
    if "tariff" in t: s -= 2
    if "inflation" in t and any(w in t for w in ["hot","surge","spike","rises"]): s -= 2
    return s

def sector_tags(text):
    t = text.lower()
    tags = [sec for sec, kws in SECTOR_KW.items() if any(k in t for k in kws)]
    return ", ".join(tags[:3]) if tags else ""

def overall_news_bias(df):
    if df.empty: return {"score": 0, "label": "MIXED", "reason": "No news"}
    total = int(df["score"].sum())
    label = "POSITIVE" if total >= 6 else ("NEGATIVE" if total <= -6 else "MIXED")
    r = []
    if any(df["bucket"].eq("india_policy")): r.append("Govt policy active")
    if any(df["title"].str.contains("oil|crude",case=False,na=False)): r.append("Oil headlines")
    if any(df["title"].str.contains("rbi|repo|rate",case=False,na=False)): r.append("RBI/rate news")
    if any(df["title"].str.contains("tariff|trump",case=False,na=False)): r.append("US policy risk")
    return {"score": total, "label": label, "reason": " · ".join(r) or "Mixed flow",
            "top_pos": df[df["score"]>0].head(4)["title"].tolist(),
            "top_neg": df[df["score"]<0].head(4)["title"].tolist()}

# ──────────────────────────────────────────────────────────────────
# SCORING ENGINE
# ──────────────────────────────────────────────────────────────────
def calculate_score(df):
    if df.empty or len(df) < 50:
        return 0, "avoid", "Insufficient Data"
    
    latest = df.iloc[-1]
    score = 50  # Base Score
    reasons = []

    # 1. Moving Averages Trend
    if latest["Close"] > latest["EMA20"]: 
        score += 10
    if latest["EMA20"] > latest["EMA50"]: 
        score += 10
    if latest["Close"] < latest["EMA20"] and latest["Close"] < latest["EMA50"]:
        score -= 20
        reasons.append("Below EMAs")

    # 2. RSI Momentum
    rsi = latest["RSI14"]
    if 40 <= rsi <= 65:
        score += 10
    elif rsi > 70:
        score -= 15
        reasons.append("Overbought")
    elif rsi < 30:
        score -= 10
        reasons.append("Oversold")

    # 3. Volume Analysis
    vol_r = latest["VOL_R"]
    if vol_r > 1.5:
        score += 15
        reasons.append("High Vol")
    elif vol_r < 0.8:
        score -= 5

    # 4. MACD Crossover
    if latest["MACD"] > latest["MACD_S"]:
        score += 10
    else:
        score -= 10
    if latest["MACD_H"] > 0:
        score += 5

    # 5. Bollinger Bands
    if latest["Close"] > latest["BB_U"]:
        score -= 10
        reasons.append("Outside BB")
    
    # Final clamping
    score = max(0, min(100, score))

    if score >= 75:
        signal = "buy"
    elif score >= 50:
        signal = "watch"
    else:
        signal = "avoid"

    reason_str = ", ".join(reasons) if reasons else "Neutral Setup"
    return score, signal, reason_str


# ──────────────────────────────────────────────────────────────────
# MAIN UI APPLICATION
# ──────────────────────────────────────────────────────────────────
def main():
    # Topbar
    curr_time = datetime.now(IST).strftime("%I:%M %p")
    st.markdown(f"""
    <div class="topbar">
        <div>
            <div class="logo">MARKETSENSE PRO</div>
            <span class="logo-sub">INTELLIGENCE TERMINAL V7</span>
        </div>
        <div class="topbar-pills">
            <span class="pill pg">SYSTEM ACTIVE</span>
            <span class="pill pb">DATA LIVE</span>
        </div>
        <div class="topbar-time">
            MUSCAT / IST<br><b>{curr_time}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Global Data Fetch
    global_q = fetch_global()
    
    # Ticker Tape
    ticker_html = "<div class='ticker-wrap'><div class='ticker-inner'>"
    for name, q in global_q.items():
        if not q: continue
        chg = q['chg']
        color_class = "t-chg-up" if chg >= 0 else "t-chg-dn"
        ticker_html += f"<div class='t-item'><span class='t-sym'>{name}</span><span class='t-price'>{q['last']:.2f}</span><span class='{color_class}'>{chg:+.2f}%</span></div>"
    ticker_html += "</div></div>"
    st.markdown(ticker_html, unsafe_allow_html=True)

    # Market Data
    prices = parallel_prices(UNIVERSE)
    
    st.markdown("<div class='sec'>🔥 TOP OPPORTUNITIES</div>", unsafe_allow_html=True)
    
    # Generate Trade Cards
    cards_html = "<div class='trade-grid'>"
    
    scored_stocks = []
    for sym, raw_df in prices.items():
        enriched = enrich(raw_df)
        if enriched.empty: continue
        
        score, signal, reason = calculate_score(enriched)
        info = UNIVERSE[sym]
        latest_c = enriched['Close'].iloc[-1]
        pct_c = enriched['RET1'].iloc[-1] * 100
        setup = setup_label(enriched.iloc[-1])
        
        scored_stocks.append({
            "sym": sym, "name": info["name"], "sector": info["sector"],
            "score": score, "signal": signal, "setup": setup, 
            "price": latest_c, "pct": pct_c, "reason": reason
        })
    
    # Sort by score descending
    scored_stocks.sort(key=lambda x: x['score'], reverse=True)
    
    for stock in scored_stocks[:8]: # Display top 8
        color_class = "buy" if stock['signal'] == 'buy' else "watch" if stock['signal'] == 'watch' else "avoid"
        bar_class = "tcbg" if stock['signal'] == 'buy' else "tcba" if stock['signal'] == 'watch' else "tcbr"
        price_color = "v-up" if stock['pct'] >= 0 else "v-dn"
        
        cards_html += f"""
        <div class="trade-card {color_class}">
            <div class="tc-score">
                <div class="score-ring"><div class="score-ring-inner"></div><span class="score-ring-val">{stock['score']}</span></div>
                <div>
                    <div class="tc-signal {color_class}">{stock['signal'].upper()}</div>
                    <div class="tc-setup">{stock['setup']}</div>
                </div>
            </div>
            <div class="tc-sym">{stock['sym']}</div>
            <div class="tc-name">{stock['name']}</div>
            <div class="tc-sector">{stock['sector']}</div>
            <div class="tc-bar"><div class="tc-bar-fill {bar_class}" style="width:{stock['score']}%;"></div></div>
            <div class="tc-row"><span class="k">Price</span><span class="v">₹{stock['price']:.2f}</span></div>
            <div class="tc-row"><span class="k">Day Chg</span><span class="v {price_color}">{stock['pct']:+.2f}%</span></div>
            <div class="tc-why">{stock['reason']}</div>
        </div>
        """
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)
    
    # Market Sentiment / News
    st.markdown("<div class='sec'>📰 MARKET SENTIMENT</div>", unsafe_allow_html=True)
    news_df = collect_all_news()
    bias = overall_news_bias(news_df)
    
    st.markdown(f"""
    <div class="regime-bar">
        <div class="regime-label">MACRO BIAS: {bias['label']}</div>
        <div class="regime-track"><div class="regime-fill" style="width: {min(100, max(0, 50 + (bias['score']*5)))}%;"></div></div>
        <div class="regime-score">Score: {bias['score']}</div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
