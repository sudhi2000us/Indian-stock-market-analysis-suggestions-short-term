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

/* ── SECTOR TILES ── */
.sec-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin-bottom:16px;}
.sec-tile{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:13px 15px;text-align:center;}
.sec-tile-name{font-size:.8rem;font-weight:700;color:#fff;margin-bottom:6px;}
.sec-tile-score{font-family:'Bebas Neue',sans-serif;font-size:1.5rem;letter-spacing:.05em;}
.sec-tile-meta{font-size:.69rem;color:var(--muted);margin-top:4px;}

/* ── MINI BAR ── */
.mbar{height:4px;border-radius:999px;background:rgba(255,255,255,.07);overflow:hidden;margin-top:5px;}
.mbar-fill{height:100%;border-radius:999px;}

/* ── GLOBAL GRID ── */
.g-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:9px;margin-bottom:16px;}
.g-tile{background:var(--card);border:1px solid var(--border);border-radius:11px;padding:12px 13px;}
.g-name{font-family:'JetBrains Mono',monospace;font-size:.59rem;color:var(--muted);
  text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;}
.g-price{font-family:'Bebas Neue',sans-serif;font-size:1.25rem;color:#fff;letter-spacing:.03em;}
.g-chg{font-size:.77rem;font-weight:600;margin-top:3px;}

/* ── OPPORTUNITY BANNER ── */
.opp-banner{
  background:linear-gradient(135deg,rgba(13,255,176,.08),rgba(0,212,255,.05));
  border:1px solid rgba(13,255,176,.2);border-radius:14px;
  padding:16px 20px;margin-bottom:16px;
  display:flex;align-items:center;gap:16px;
}
.opp-icon{font-size:1.8rem;}
.opp-title{font-family:'Bebas Neue',sans-serif;font-size:1.1rem;letter-spacing:.06em;color:var(--green);}
.opp-desc{font-size:.83rem;color:var(--text);margin-top:2px;line-height:1.5;}

/* ── ALERT / SIGNAL ── */
.alert-row{display:flex;align-items:center;justify-content:space-between;
  padding:10px 14px;background:var(--card);border:1px solid var(--border);
  border-radius:10px;margin-bottom:7px;}
.alert-row:hover{border-color:var(--border2);}
.ar-left{display:flex;flex-direction:column;gap:2px;}
.ar-name{font-weight:700;font-size:.9rem;color:#fff;}
.ar-meta{font-size:.72rem;color:var(--muted);}
.ar-right{text-align:right;}
.ar-price{font-family:'JetBrains Mono',monospace;font-size:.88rem;font-weight:700;color:#fff;}
.ar-chg{font-size:.73rem;margin-top:2px;}

/* ── REGIME METER ── */
.regime-bar{background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:13px 18px;display:flex;align-items:center;gap:16px;margin-bottom:12px;}
.regime-track{flex:1;height:8px;background:rgba(255,255,255,.07);border-radius:999px;overflow:hidden;}
.regime-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#00c97a,var(--green),var(--cyan));}
.regime-label{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:.06em;}
.regime-score{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--muted);white-space:nowrap;}

/* ── SIZER ── */
.sizer{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px 20px;}
.sizer-title{font-family:'Bebas Neue',sans-serif;font-size:1rem;letter-spacing:.06em;color:#fff;margin-bottom:13px;}
.sizer-row{display:flex;justify-content:space-between;padding:5px 0;
  border-bottom:1px solid rgba(255,255,255,.04);font-size:.82rem;}
.sizer-row .sk{color:var(--muted);}
.sizer-row .sv{font-family:'JetBrains Mono',monospace;color:#fff;font-weight:600;}
.sv-big{color:var(--green)!important;font-size:1.1rem;font-family:'Bebas Neue',sans-serif!important;letter-spacing:.05em;}

/* ── STRIP ALERTS ── */
.strip-g{background:rgba(13,255,176,.07);border:1px solid rgba(13,255,176,.2);
  border-radius:10px;padding:10px 14px;font-size:.82rem;color:#a7f3d0;margin-bottom:8px;}
.strip-r{background:rgba(255,61,90,.07);border:1px solid rgba(255,61,90,.2);
  border-radius:10px;padding:10px 14px;font-size:.82rem;color:#fecdd3;margin-bottom:8px;}
.strip-a{background:rgba(255,183,64,.07);border:1px solid rgba(255,183,64,.2);
  border-radius:10px;padding:10px 14px;font-size:.82rem;color:#fde68a;margin-bottom:8px;}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{gap:4px;border-bottom:1px solid var(--border)!important;background:transparent!important;}
.stTabs [data-baseweb="tab"]{
  font-family:'JetBrains Mono',monospace!important;font-size:.67rem!important;
  text-transform:uppercase!important;letter-spacing:.06em;
  background:transparent!important;border:none!important;color:var(--muted)!important;
  padding:9px 15px!important;border-bottom:2px solid transparent!important;
}
[aria-selected="true"]{color:var(--green)!important;border-bottom-color:var(--green)!important;}

/* ── DATA TABLE ── */
[data-testid="stDataFrame"]{border:1px solid var(--border)!important;border-radius:10px!important;}
[data-testid="stDataFrame"] *{font-family:'JetBrains Mono',monospace!important;font-size:.72rem!important;}

/* ── PLOTLY ── */
.js-plotly-plot .plotly{background:transparent!important;}

/* ── RESPONSIVE ── */
@media(max-width:1200px){
  .stat-strip{grid-template-columns:repeat(4,1fr);}
  .trade-grid{grid-template-columns:repeat(2,1fr);}
  .g-grid{grid-template-columns:repeat(4,1fr);}
  .sec-grid{grid-template-columns:repeat(3,1fr);}
}
@media(max-width:700px){
  .stat-strip{grid-template-columns:repeat(2,1fr);}
  .trade-grid,.g-grid,.sec-grid{grid-template-columns:1fr;}
}
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
def score_stock(sym, info, enr_df, nifty_enr, news_df, regime_score, sector_rank):
    if enr_df.empty or nifty_enr.empty:
        return None
    d = enr_df.iloc[-1]; n = nifty_enr.iloc[-1]
    c = safe(d["Close"]); atr = safe(d["ATR14"])

    # ── TECHNICAL (0-100) ──
    tech = 0; tn = []
    if c > safe(d["EMA20"]):   tech += 12; tn.append("↑EMA20")
    if c > safe(d["EMA50"]):   tech += 10; tn.append("↑EMA50")
    if safe(d["EMA20"]) > safe(d["EMA50"]): tech += 8; tn.append("stack")
    if c > safe(d["EMA200"]):  tech += 5;  tn.append("↑EMA200")
    if safe(d["EMA9"]) > safe(d["EMA20"]): tech += 4
    rsi = safe(d["RSI14"])
    if 55 <= rsi <= 73:  tech += 10; tn.append(f"RSI {rsi:.0f}")
    elif rsi > 73:       tech += 4
    elif rsi < 44:       tech -= 8
    sr = safe(d["StochRSI"])
    if 18 <= sr <= 48:   tech += 5; tn.append("SR reset")
    elif sr > 82:        tech -= 4
    if safe(d["MACD_H"]) > 0: tech += 8; tn.append("MACD+")
    vr = safe(d["VOL_R"], 1.0)
    if vr >= 1.6:  tech += 10; tn.append(f"vol {vr:.1f}x")
    elif vr >= 1.2: tech += 5;  tn.append("vol↑")
    elif vr < 0.7: tech -= 5
    if safe(d["OBV"]) > safe(d["OBV_EMA"]): tech += 5; tn.append("OBV+")
    else: tech -= 3
    donch = safe(d["DONCH"], 50)
    if donch >= 88: tech += 8; tn.append("52W zone")
    elif donch >= 72: tech += 4
    elif donch < 25: tech -= 5
    # BB squeeze
    bw = safe(d["BB_W"], 5); bwa = safe(d["BB_W_AVG"], 5)
    bb_sq = not pd.isna(bw) and not pd.isna(bwa) and bw < bwa * 0.82
    if bb_sq: tech += 8; tn.append("BB squeeze🔥")
    # 52W position
    w52 = safe(d.get("52W_PCT", 50))
    if w52 >= 90: tech += 6; tn.append("near ATH")
    elif w52 >= 75: tech += 3
    # Gap + volume
    r1 = safe(d.get("RET1", 0)) * 100
    if r1 > 1.5 and vr >= 1.3: tech += 5; tn.append("gap↑")
    tech = max(0, min(100, tech))

    # ── RELATIVE STRENGTH (0-100) ──
    rs = 50; rn = []
    for ret_col, w in [("RET5",10), ("RET20",14), ("RET60",8)]:
        sv = safe(d.get(ret_col,0)); nv = safe(n.get(ret_col,0))
        if pd.isna(sv) or pd.isna(nv): continue
        diff = (sv - nv) * 100
        if diff > 5: rs += w; rn.append(f"RS+{w}")
        elif diff > 2: rs += w//2
        elif diff < -5: rs -= w
        elif diff < -2: rs -= w//2
    rs5 = (safe(d.get("RET5",0)) - safe(n.get("RET5",0))) * 100
    rs10 = (safe(d.get("RET10",0)) - safe(n.get("RET10",0))) * 100
    if not pd.isna(rs5) and not pd.isna(rs10) and rs5 > rs10:
        rs += 6; rn.append("RS accel")
    rs = max(0, min(100, rs))

    # ── NEWS IMPACT (0-100) ──
    ns_score = 50
    name = info["name"]; sector = info["sector"]
    if not news_df.empty:
        for h in news_df["title"].head(40).tolist():
            t = h.lower()
            if sym.lower() in t or name.lower() in t: ns_score += 8
            if sector.lower() in t: ns_score += 2
            for kw in SECTOR_KW.get(sector, []):
                if kw in t: ns_score += 1
    ns_score = max(0, min(100, ns_score))

    # ── SECTOR SCORE ──
    sec_sc = safe(sector_rank.get(info["sector"], 50))

    # ── COMPOSITE ──
    base = (0.35 * tech + 0.18 * rs + 0.17 * sec_sc + 0.15 * ns_score + 0.15 * regime_score)
    final = round(max(0, min(100, base)), 2)

    setup = setup_label(d)
    conf = "HIGH" if final >= 70 else ("MED" if final >= 55 else "LOW")
    if final >= 70: signal = "BUY NOW"
    elif final >= 58: signal = "WATCH"
    elif final >= 46: signal = "AGGRESSIVE"
    else: signal = "AVOID"

    # Stop/target
    if pd.isna(atr) or atr <= 0: sl = round(c * 0.95, 2)
    else:
        mult = {"BB Squeeze 🔥":1.0,"Vol Breakout 🚀":1.1,"Breakout":1.3,
                "Momentum":1.1,"EMA Pullback":1.6,"Bounce":1.8,
                "StochRSI Reset":1.5,"Trend":1.4}.get(setup, 1.4)
        sl = round(c - mult * atr, 2)
    risk = max(c - sl, 0.01)
    t1 = round(c + 2.0 * risk, 2)
    t2 = round(c + 3.5 * risk, 2)
    pp1 = round(((t1/c)-1)*100, 2); pp2 = round(((t2/c)-1)*100, 2)
    sl_pct = round((1 - sl/c)*100, 2); rr = round((t1-c)/risk, 2)

    why_parts = tn[:3] + rn[:1]
    if bb_sq: why_parts.append("BB compression→breakout pending")
    if w52 >= 88: why_parts.append("near 52W high — momentum")
    why = " · ".join(why_parts)

    return {
        "symbol": sym, "name": name, "sector": sector,
        "signal": signal, "confidence": conf, "setup": setup,
        "score": final, "tech": round(tech,1), "rs": round(rs,1),
        "news_sc": round(ns_score,1), "sec_sc": round(sec_sc,1),
        "ltp": round(c,2), "t1": t1, "t2": t2, "pp1": pp1, "pp2": pp2,
        "sl": sl, "sl_pct": sl_pct, "rr": rr,
        "rsi": round(rsi,1), "vr": round(vr,2), "donch": round(donch,1),
        "bb_squeeze": bb_sq, "w52": round(w52,1),
        "obv_pos": safe(d["OBV"]) > safe(d["OBV_EMA"]),
        "why": why,
        "horizon": "1–3 days (intraday/swing)" if pp1 < 5 else "3–10 days (swing)",
    }

def compute_sector_ranks(stock_rows):
    if not stock_rows: return {}
    df = pd.DataFrame([r for r in stock_rows if r is not None])
    if df.empty or "sector" not in df.columns: return {}
    grp = df.groupby("sector")["score"].mean().to_dict()
    return grp

def market_regime(nifty_enr, vix_last, nb, breadth_pct, global_data):
    if nifty_enr.empty: return {"label":"NEUTRAL","score":50,"reason":"No data"}
    sc = 50; r = []
    d = nifty_enr.iloc[-1]
    if d["Close"] > d["EMA20"]: sc += 8; r.append("↑EMA20")
    else: sc -= 8
    if d["EMA20"] > d["EMA50"]: sc += 10; r.append("EMA stack")
    else: sc -= 10
    if d["Close"] > d["EMA200"]: sc += 6; r.append("↑EMA200")
    else: sc -= 6
    rsi_v = safe(d["RSI14"])
    if rsi_v > 57: sc += 7; r.append(f"RSI {rsi_v:.0f}")
    elif rsi_v < 43: sc -= 7
    if safe(d["MACD_H"]) > 0: sc += 7; r.append("MACD+")
    else: sc -= 7
    if not pd.isna(vix_last):
        if vix_last > 22: sc -= 10; r.append(f"VIX {vix_last:.1f}↑")
        elif vix_last < 14: sc += 5; r.append(f"VIX {vix_last:.1f} calm")
    bp = safe(breadth_pct, 50)
    if bp >= 62: sc += 8; r.append(f"breadth {bp:.0f}%")
    elif bp >= 53: sc += 4
    elif bp <= 40: sc -= 8
    sc += max(-8, min(8, nb["score"]))
    # Global: US market influence
    spx = global_data.get("S&P 500", {}).get("chg", np.nan)
    if not np.isnan(spx):
        if spx > 0.5: sc += 5; r.append("Wall St↑")
        elif spx < -0.5: sc -= 5; r.append("Wall St↓")
    sc = max(0, min(100, sc))
    label = "BULLISH" if sc >= 66 else ("BEARISH" if sc <= 36 else "NEUTRAL")
    return {"label": label, "score": round(sc,1), "reason": " · ".join(r[:6])}

# ──────────────────────────────────────────────────────────────────
# CHART BUILDERS
# ──────────────────────────────────────────────────────────────────
CHART_STYLE = dict(
    paper_bgcolor="#111422", plot_bgcolor="#111422",
    font=dict(color="#636d8a", family="JetBrains Mono, monospace", size=10),
    margin=dict(l=8, r=8, t=28, b=8),
)

def candle_chart(df, enr, sym):
    if df.empty: return None
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.60, 0.20, 0.20], vertical_spacing=0.02,
                        subplot_titles=[f"  {sym}", "  Volume", "  RSI 14"])
    # Candles
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing_line_color="#0dffb0", decreasing_line_color="#ff3d5a",
        increasing_fillcolor="rgba(13,255,176,0.55)", decreasing_fillcolor="rgba(255,61,90,0.55)",
        name="Price", showlegend=False
    ), row=1, col=1)
    # EMAs
    if enr is not None and not enr.empty:
        for ema, col in [("EMA20","#3d9eff"),("EMA50","#ffb740"),("EMA200","#b57bff")]:
            if ema in enr.columns:
                fig.add_trace(go.Scatter(x=enr.index, y=enr[ema], name=ema,
                                          line=dict(color=col, width=1.2), opacity=0.9,
                                          showlegend=True), row=1, col=1)
        # BB
        if "BB_U" in enr.columns:
            fig.add_trace(go.Scatter(x=enr.index, y=enr["BB_U"], showlegend=False,
                                      line=dict(color="rgba(181,123,255,0.35)",width=1,dash="dot")), row=1, col=1)
            fig.add_trace(go.Scatter(x=enr.index, y=enr["BB_L"], showlegend=False,
                                      line=dict(color="rgba(181,123,255,0.35)",width=1,dash="dot"),
                                      fill="tonexty", fillcolor="rgba(181,123,255,0.04)"), row=1, col=1)
        # Volume
        vol_colors = ["#0dffb0" if c >= o else "#ff3d5a"
                      for c, o in zip(df["Close"], df["Open"])]
        fig.add_trace(go.Bar(x=df.index, y=df["Volume"], marker_color=vol_colors,
                              opacity=0.7, showlegend=False), row=2, col=1)
        if "VOL20" in enr.columns:
            fig.add_trace(go.Scatter(x=enr.index, y=enr["VOL20"],
                                      line=dict(color="#ffb740",width=1), showlegend=False), row=2, col=1)
        # RSI
        if "RSI14" in enr.columns:
            fig.add_trace(go.Scatter(x=enr.index, y=enr["RSI14"],
                                      line=dict(color="#00d4ff",width=1.5), showlegend=False), row=3, col=1)
            for lvl, col in [(70,"rgba(255,61,90,0.35)"),(30,"rgba(13,255,176,0.35)"),(50,"rgba(255,255,255,0.08)")]:
                fig.add_hline(y=lvl, line_dash="dot", line_color=col, row=3, col=1)

    fig.update_layout(**CHART_STYLE, height=520, showlegend=True,
                      legend=dict(orientation="h", y=1.06, font=dict(size=9),
                                  bgcolor="rgba(0,0,0,0)"),
                      xaxis_rangeslider_visible=False)
    for i in range(1, 4):
        fig.update_xaxes(gridcolor="rgba(255,255,255,0.04)", showgrid=True, zeroline=False, row=i, col=1)
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.04)", showgrid=True, zeroline=False, row=i, col=1)
    return fig

def nifty_mini_chart(enr):
    if enr is None or enr.empty: return None
    df = enr.tail(90)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="NIFTY",
                              line=dict(color="#0dffb0",width=2),
                              fill="tozeroy", fillcolor="rgba(13,255,176,0.05)"))
    for ema, c in [("EMA20","#3d9eff"),("EMA50","#ffb740")]:
        fig.add_trace(go.Scatter(x=df.index, y=df[ema], name=ema,
                                  line=dict(color=c,width=1,dash="dot")))
    fig.update_layout(**CHART_STYLE, height=200, showlegend=False,
                      margin=dict(l=8,r=8,t=10,b=8))
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.03)", showgrid=True, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.03)", showgrid=True, zeroline=False)
    return fig

def sector_bar_chart(sector_df):
    if sector_df.empty: return None
    fig = go.Figure(go.Bar(
        x=sector_df["sector"], y=sector_df["avg_score"],
        marker_color=[("#0dffb0" if v >= 65 else ("#ffb740" if v >= 50 else "#ff3d5a"))
                      for v in sector_df["avg_score"]],
        text=sector_df["avg_score"].round(1), textposition="outside",
        textfont=dict(size=9, color=["#0dffb0" if v >= 65 else ("#ffb740" if v >= 50 else "#ff3d5a")
                                     for v in sector_df["avg_score"]]),
    ))
    fig.update_layout(**CHART_STYLE, height=220, showlegend=False,
                      xaxis=dict(tickangle=-30, tickfont=dict(size=9)),
                      yaxis=dict(range=[0,100], showgrid=True,
                                 gridcolor="rgba(255,255,255,0.04)"),
                      margin=dict(l=8,r=8,t=15,b=50))
    return fig

# ──────────────────────────────────────────────────────────────────
# UI HELPERS
# ──────────────────────────────────────────────────────────────────
def pill(label, kind="b"):
    css = {"g":"pg","r":"pr","a":"pa","b":"pb","p":"pp"}.get(kind,"pb")
    return f'<span class="pill {css}">{label}</span>'

def regime_pill(label):
    m = {"BULLISH":"g","BEARISH":"r","NEUTRAL":"a","POSITIVE":"g","NEGATIVE":"r","MIXED":"a",
         "BULLISH OPEN":"g","WEAK OPEN":"r","MIXED OPEN":"a","BUY NOW":"g","WATCH":"a","AVOID":"r","TRADABLE":"g"}
    return pill(label, m.get(label,"b"))

def score_ring_html(score, sz=40):
    pct_v = max(0, min(100, safe(score, 0)))
    col = "var(--green)" if pct_v >= 65 else ("var(--amber)" if pct_v >= 48 else "var(--red)")
    conic = f"conic-gradient({col} {pct_v*3.6:.0f}deg, rgba(255,255,255,0.06) 0)"
    return (f'<div class="score-ring" style="background:{conic};width:{sz}px;height:{sz}px;">'
            f'<div class="score-ring-inner"></div>'
            f'<span class="score-ring-val">{pct_v:.0f}</span></div>')

def bar(pct_v, cls="tcbg"):
    v = max(0, min(100, safe(pct_v, 0)))
    return f'<div class="tc-bar"><div class="tc-bar-fill {cls}" style="width:{v:.0f}%"></div></div>'

def mini_bar(val, max_val=100, color="var(--green)"):
    w = max(0, min(100, val/max_val*100)) if max_val > 0 else 0
    return f'<div class="mbar"><div class="mbar-fill" style="width:{w:.0f}%;background:{color};"></div></div>'

# ──────────────────────────────────────────────────────────────────
# MAIN DATA LOAD (with spinner)
# ──────────────────────────────────────────────────────────────────
now_ist = datetime.now(IST)
sess_label = "Live" if (now_ist.weekday() < 5 and
                         time(9,15) <= now_ist.time() <= time(15,30)) else "After Hours"

# Topbar placeholder (renders immediately)
st.markdown(f"""
<div class="topbar">
  <div>
    <div class="logo">MARKETSENSE PRO</div>
    <span class="logo-sub">INDIA SHORT-TERM INTELLIGENCE TERMINAL</span>
  </div>
  <div class="topbar-pills" id="topbar-pills-placeholder">
    {pill('Loading...','b')}
  </div>
  <div class="topbar-time">
    <b>{now_ist.strftime('%d %b %Y')}</b> · {now_ist.strftime('%H:%M IST')}<br>
    Auto-refresh every 5 min · {sess_label}
  </div>
</div>
""", unsafe_allow_html=True)

with st.spinner("⚡ Fetching live data & running intelligence engine..."):
    # Parallel fetches
    all_hist   = parallel_prices(UNIVERSE)
    all_quotes = parallel_quotes(UNIVERSE)
    global_q   = fetch_global()
    nifty_raw  = fetch_price("^NSEI", "1y")
    nifty_enr  = enrich(nifty_raw)
    vix_raw    = fetch_price("^INDIAVIX", "1y")
    vix_last   = safe(vix_raw["Close"].iloc[-1]) if not vix_raw.empty else np.nan
    nifty_q    = fetch_quote("^NSEI")
    news_all   = collect_all_news()
    nb         = overall_news_bias(news_all)

    # Breadth (simple: count stocks above EMA20)
    above_ema20 = sum(1 for sym in UNIVERSE if not enrich(all_hist.get(sym, pd.DataFrame())).empty
                      and safe(enrich(all_hist.get(sym,pd.DataFrame())).iloc[-1]["Close"]) >
                      safe(enrich(all_hist.get(sym,pd.DataFrame())).iloc[-1]["EMA20"]))
    breadth_pct = (above_ema20 / len(UNIVERSE)) * 100

    # Phase 1 — score without sector rank
    p1_rows = []
    for sym, info in UNIVERSE.items():
        enr_df = enrich(all_hist.get(sym, pd.DataFrame()))
        row = score_stock(sym, info, enr_df, nifty_enr, news_all, 50, {})
        if row: p1_rows.append(row)
    sector_rank = compute_sector_ranks(p1_rows)

    # Regime (uses sector-aware data now)
    regime = market_regime(nifty_enr, vix_last, nb, breadth_pct, global_q)

    # Phase 2 — final score with sector rank + regime
    final_rows = []
    for sym, info in UNIVERSE.items():
        enr_df = enrich(all_hist.get(sym, pd.DataFrame()))
        row = score_stock(sym, info, enr_df, nifty_enr, news_all, regime["score"], sector_rank)
        if row: final_rows.append(row)

    rank_df = pd.DataFrame(final_rows).sort_values("score", ascending=False).reset_index(drop=True)
    rank_df["rank"] = range(1, len(rank_df)+1)

    # Sector table
    sec_agg = rank_df.groupby("sector").agg(
        avg_score=("score","mean"),
        buy_count=("signal", lambda s:(s=="BUY NOW").sum()),
        stocks=("symbol","count"),
    ).reset_index().sort_values("avg_score", ascending=False)

    # Filtered buckets
    buy_now  = rank_df[rank_df["signal"]=="BUY NOW"].head(8)
    watch    = rank_df[rank_df["signal"]=="WATCH"].head(6)
    bb_sq    = rank_df[rank_df["bb_squeeze"]==True].head(6)
    near_ath = rank_df[rank_df["w52"]>=85].head(6)

    # Day verdict
    dv_score = (regime["score"]-50)/4.5 + max(-3,min(3,nb["score"]/2))
    if not pd.isna(vix_last):
        if vix_last > 22: dv_score -= 3
        elif vix_last < 14: dv_score += 1
    if dv_score >= 5: dv = {"verdict":"TRADABLE","msg":"Conditions strong — size up on A-grade setups."}
    elif dv_score <= -5: dv = {"verdict":"AVOID","msg":"Unstable — protect capital, very selective."}
    else: dv = {"verdict":"SELECTIVE","msg":"Mixed — only high-conviction entries, tight stops."}

# ──────────────────────────────────────────────────────────────────
# TOPBAR (re-render with real data)
# ──────────────────────────────────────────────────────────────────
nifty_chg  = safe(nifty_q.get("chg"), 0)
nifty_last = safe(nifty_q.get("last"), 0)
st.markdown(f"""
<div class="topbar">
  <div>
    <div class="logo">MARKETSENSE PRO</div>
    <span class="logo-sub">INDIA SHORT-TERM INTELLIGENCE TERMINAL</span>
  </div>
  <div class="topbar-pills">
    {regime_pill(regime['label'])}
    {regime_pill(dv['verdict'])}
    {regime_pill(nb['label'])}
    {pill(sess_label,'b')}
    {pill(f"VIX {vix_last:.1f}",'g' if vix_last<16 else ('r' if vix_last>22 else 'a'))}
    {pill(f"NIFTY {'▲' if nifty_chg>=0 else '▼'}{abs(nifty_chg):.2f}%",'g' if nifty_chg>=0 else 'r')}
  </div>
  <div class="topbar-time">
    <b>{now_ist.strftime('%d %b %Y')}</b> · {now_ist.strftime('%H:%M IST')}<br>
    ⚡ Auto-refresh 5 min · {len(final_rows)} stocks scanned
  </div>
</div>
""", unsafe_allow_html=True)

# ── LIVE TICKER TAPE ──
tape_items = []
for sym, q in list(all_quotes.items())[:20]:
    if not q: continue
    chg = safe(q.get("chg"), 0)
    ar = "▲" if chg >= 0 else "▼"
    cc = "t-chg-up" if chg >= 0 else "t-chg-dn"
    ltp = safe(q.get("last"), 0)
    tape_items.append(
        f'<span class="t-item"><span class="t-sym">{sym}</span>'
        f'<span class="t-price">₹{ltp:,.2f}</span>'
        f'<span class="{cc}">{ar}{abs(chg):.2f}%</span></span>'
    )
tape_html = " ".join(tape_items * 3)  # triple for seamless loop
st.markdown(f'<div class="ticker-wrap"><div class="ticker-inner">{tape_html}</div></div>',
            unsafe_allow_html=True)

# ── STAT STRIP ──
brent_q   = global_q.get("BRENT", {})
brent_chg = safe(brent_q.get("chg"), 0)
brent_val = safe(brent_q.get("last"), 0)
gold_q    = global_q.get("GOLD", {})
gold_chg  = safe(gold_q.get("chg"), 0)
usd_q     = global_q.get("USD/INR", {})
usd_chg   = safe(usd_q.get("chg"), 0)
usd_last  = safe(usd_q.get("last"), 0)
spx_q     = global_q.get("S&P 500", {})
spx_chg   = safe(spx_q.get("chg"), 0)

vix_col = "sg" if vix_last < 16 else ("sr" if vix_last > 22 else "sa")
vix_lbl = "calm" if vix_last < 16 else ("elevated" if vix_last > 22 else "moderate")
brent_col = "sr" if brent_chg > 1 else ("sg" if brent_chg < -1 else "sa")

st.markdown(f"""
<div class="stat-strip">
  <div class="stat {'sg' if nifty_chg>=0 else 'sr'}">
    <div class="stat-lbl">NIFTY 50</div>
    <div class="stat-val">{nifty_last:,.0f}</div>
    <div class="stat-sub {'sup' if nifty_chg>=0 else 'sdn'}">{'▲' if nifty_chg>=0 else '▼'} {abs(nifty_chg):.2f}%</div>
  </div>
  <div class="stat {vix_col}">
    <div class="stat-lbl">INDIA VIX</div>
    <div class="stat-val">{vix_last:.1f}</div>
    <div class="stat-sub sneu">{vix_lbl}</div>
  </div>
  <div class="stat {'sg' if breadth_pct>=55 else ('sr' if breadth_pct<45 else 'sa')}">
    <div class="stat-lbl">Breadth</div>
    <div class="stat-val">{breadth_pct:.0f}%</div>
    <div class="stat-sub sneu">above EMA20</div>
  </div>
  <div class="stat {'sg' if spx_chg>=0 else 'sr'}">
    <div class="stat-lbl">S&P 500</div>
    <div class="stat-val">{'▲' if spx_chg>=0 else '▼'}{abs(spx_chg):.2f}%</div>
    <div class="stat-sub sneu">overnight</div>
  </div>
  <div class="stat {brent_col}">
    <div class="stat-lbl">BRENT</div>
    <div class="stat-val">${brent_val:.1f}</div>
    <div class="stat-sub {'sdn' if brent_chg>0 else 'sup'}">{brent_chg:+.2f}%</div>
  </div>
  <div class="stat {'sg' if gold_chg>=0 else 'sr'}">
    <div class="stat-lbl">GOLD</div>
    <div class="stat-val">{'▲' if gold_chg>=0 else '▼'}{abs(gold_chg):.2f}%</div>
    <div class="stat-sub sneu">XAU/USD</div>
  </div>
  <div class="stat {'sr' if usd_chg>0.2 else ('sg' if usd_chg<-0.2 else 'sa')}">
    <div class="stat-lbl">USD/INR</div>
    <div class="stat-val">{usd_last:.2f}</div>
    <div class="stat-sub {'sdn' if usd_chg>0.2 else 'sneu'}">{usd_chg:+.2f}%</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── OPPORTUNITY BANNER ──
if regime["label"] == "BULLISH" and dv["verdict"] == "TRADABLE":
    top_sym = buy_now.iloc[0] if not buy_now.empty else None
    banner_desc = (f"Market is in BULLISH regime with {breadth_pct:.0f}% stocks above EMA20. "
                   f"News sentiment: {nb['label']}. {nb['reason']}. "
                   + (f"Top setup: <b>{top_sym['name']}</b> ({top_sym['setup']})" if top_sym is not None else ""))
    st.markdown(f"""
    <div class="opp-banner">
      <div class="opp-icon">🚀</div>
      <div>
        <div class="opp-title">CONDITIONS FAVOURABLE — GO LONG</div>
        <div class="opp-desc">{banner_desc}</div>
      </div>
    </div>""", unsafe_allow_html=True)
elif regime["label"] == "BEARISH":
    st.markdown('<div class="strip-r">⚠️ <b>BEARISH REGIME</b> — Avoid fresh long positions. Capital protection is priority. Wait for regime to improve.</div>', unsafe_allow_html=True)
else:
    st.markdown(f'<div class="strip-a">⚡ <b>{dv["verdict"]}</b> — {dv["msg"]} Regime: {regime["label"]} ({regime["score"]}/100). News: {nb["label"]}.</div>', unsafe_allow_html=True)

# ── NIFTY MINI CHART + REGIME ──
chart_col, regime_col = st.columns([2, 1])
with chart_col:
    st.markdown('<div class="sec">NIFTY 50 — LIVE TREND</div>', unsafe_allow_html=True)
    nmf = nifty_mini_chart(nifty_enr)
    if nmf: st.plotly_chart(nmf, use_container_width=True, config={"displayModeBar":False})

with regime_col:
    st.markdown('<div class="sec">MARKET REGIME</div>', unsafe_allow_html=True)
    reg_col_str = {"BULLISH":"var(--green)","BEARISH":"var(--red)","NEUTRAL":"var(--amber)"}.get(regime["label"],"var(--amber)")
    st.markdown(f"""
    <div class="regime-bar">
      <div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px;">Regime</div>
        <div class="regime-label" style="color:{reg_col_str};">{regime['label']}</div>
      </div>
      <div class="regime-track"><div class="regime-fill" style="width:{regime['score']}%"></div></div>
      <div class="regime-score">{regime['score']}/100</div>
    </div>
    <div style="font-size:.78rem;color:var(--muted);line-height:1.7;margin-top:6px;">
      <b style="color:var(--text);">Drivers:</b><br>
      {regime['reason']}<br><br>
      <b style="color:var(--text);">News:</b><br>
      {nb['reason']}<br><br>
      <b style="color:var(--text);">VIX:</b> {vix_last:.1f} ({vix_lbl}) &nbsp;·&nbsp;
      <b style="color:var(--text);">Breadth:</b> {breadth_pct:.0f}%
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🎯 Best Trades", "🔥 Special Setups",
    "📰 News Impact", "📈 Deep Dive",
    "🏆 Sectors", "🌍 Global", "📋 Full Scan"
])

# ══════════════════════════════════════════════════════════════════
# TAB 0 — BEST TRADES
# ══════════════════════════════════════════════════════════════════
with tabs[0]:
    # ── BUY NOW CARDS ──
    st.markdown('<div class="sec">TOP BUY NOW — SHORT-TERM MOMENTUM PICKS</div>', unsafe_allow_html=True)

    if buy_now.empty:
        st.markdown('<div class="strip-r">No BUY NOW signals under current regime. Market conditions do not favour fresh longs.</div>', unsafe_allow_html=True)
    else:
        n_cols = min(4, len(buy_now))
        cols = st.columns(n_cols)
        for col, (_, row) in zip(cols, buy_now.head(n_cols).iterrows()):
            bar_cls = "tcbg" if row["score"] >= 65 else ("tcba" if row["score"] >= 50 else "tcbr")
            sq_icon = "🔥" if row["bb_squeeze"] else ""
            ath_icon = "🏔️" if row["w52"] >= 88 else ""
            with col:
                st.markdown(f"""
                <div class="trade-card buy">
                  <div class="tc-sym">{row['symbol']} · {row['sector']}</div>
                  <div class="tc-name">{row['name']}</div>
                  <div class="tc-sector">{sq_icon}{ath_icon} {row['setup']}</div>
                  <div class="tc-score">
                    {score_ring_html(row['score'],42)}
                    <div>
                      <div class="tc-signal buy">BUY NOW</div>
                      <div style="font-size:.68rem;color:var(--muted);">{row['confidence']} confidence</div>
                    </div>
                  </div>
                  {bar(row['score'],bar_cls)}
                  <div class="tc-row"><span class="k">LTP</span><span class="v">₹{row['ltp']:,.2f}</span></div>
                  <div class="tc-row"><span class="k">Target 1</span><span class="v v-up">₹{row['t1']:,.2f} · +{row['pp1']}%</span></div>
                  <div class="tc-row"><span class="k">Target 2</span><span class="v v-up">₹{row['t2']:,.2f} · +{row['pp2']}%</span></div>
                  <div class="tc-row"><span class="k">Stop Loss</span><span class="v v-dn">₹{row['sl']:,.2f} · -{row['sl_pct']}%</span></div>
                  <div class="tc-row"><span class="k">Risk:Reward</span><span class="v">{row['rr']}</span></div>
                  <div class="tc-row"><span class="k">RSI · Vol</span><span class="v">{row['rsi']} · {row['vr']:.1f}x</span></div>
                  <div class="tc-row"><span class="k">52W Position</span><span class="v">{'🔥 ' if row['w52']>=88 else ''}{row['w52']:.0f}%</span></div>
                  <div class="tc-row"><span class="k">Horizon</span><span class="v">{row['horizon']}</span></div>
                  <div class="tc-why">{row['why']}</div>
                </div>""", unsafe_allow_html=True)

    # ── Row 2: WATCH cards ──
    if not watch.empty:
        st.markdown('<div class="sec">WATCH LIST — BUILDING SETUPS</div>', unsafe_allow_html=True)
        wn = min(4, len(watch))
        wcols = st.columns(wn)
        for col, (_, row) in zip(wcols, watch.head(wn).iterrows()):
            sq_icon = "🔥" if row["bb_squeeze"] else ""
            with col:
                st.markdown(f"""
                <div class="trade-card watch">
                  <div class="tc-sym">{row['symbol']} · {row['sector']}</div>
                  <div class="tc-name">{row['name']}</div>
                  <div class="tc-sector">{sq_icon} {row['setup']}</div>
                  <div class="tc-score">
                    {score_ring_html(row['score'],40)}
                    <div>
                      <div class="tc-signal watch">WATCH</div>
                      <div style="font-size:.68rem;color:var(--muted);">Confirm before entry</div>
                    </div>
                  </div>
                  {bar(row['score'],'tcba')}
                  <div class="tc-row"><span class="k">LTP</span><span class="v">₹{row['ltp']:,.2f}</span></div>
                  <div class="tc-row"><span class="k">Target 1</span><span class="v v-up">+{row['pp1']}%</span></div>
                  <div class="tc-row"><span class="k">Stop Loss</span><span class="v v-dn">-{row['sl_pct']}%</span></div>
                  <div class="tc-row"><span class="k">RSI · Vol</span><span class="v">{row['rsi']} · {row['vr']:.1f}x</span></div>
                  <div class="tc-why">{row['why']}</div>
                </div>""", unsafe_allow_html=True)

    # ── Position Sizer ──
    st.markdown('<div class="sec">POSITION SIZER — RISK MANAGEMENT</div>', unsafe_allow_html=True)
    ps_l, ps_r = st.columns([1,1])
    with ps_l:
        capital = st.number_input("Capital (₹)", min_value=10_000, value=100_000, step=10_000, key="cap")
        risk_pct = st.slider("Risk per trade (%)", 0.25, 2.0, 1.0, 0.25, key="rsk")
    with ps_r:
        if not buy_now.empty:
            sel = st.selectbox("Select idea", buy_now["symbol"].tolist() + (watch["symbol"].tolist() if not watch.empty else []), key="ps_sel")
            sel_row = rank_df[rank_df["symbol"]==sel]
            if not sel_row.empty:
                r = sel_row.iloc[0]
                risk_amt = capital * (risk_pct/100)
                per_share = max(r["ltp"]-r["sl"], 0.01)
                qty = int(risk_amt // per_share)
                invest = round(qty * r["ltp"], 0)
                t1_pnl = round(qty * (r["t1"]-r["ltp"]), 0)
                t2_pnl = round(qty * (r["t2"]-r["ltp"]), 0)
                st.markdown(f"""
                <div class="sizer">
                  <div class="sizer-title">📐 {r['name']} ({r['symbol']})</div>
                  <div class="sizer-row"><span class="sk">Capital</span><span class="sv">₹{capital:,.0f}</span></div>
                  <div class="sizer-row"><span class="sk">Max risk ({risk_pct}%)</span><span class="sv">₹{risk_amt:,.0f}</span></div>
                  <div class="sizer-row"><span class="sk">Entry</span><span class="sv">₹{r['ltp']:,.2f}</span></div>
                  <div class="sizer-row"><span class="sk">Stop Loss</span><span class="sv">₹{r['sl']:,.2f} (-{r['sl_pct']}%)</span></div>
                  <div class="sizer-row"><span class="sk">Risk / share</span><span class="sv">₹{per_share:,.2f}</span></div>
                  <div class="sizer-row"><span class="sk">Quantity</span><span class="sv sv-big">{qty} shares</span></div>
                  <div class="sizer-row"><span class="sk">Investment</span><span class="sv">₹{invest:,.0f} ({invest/capital*100:.1f}%)</span></div>
                  <div class="sizer-row"><span class="sk">Target 1 P&L</span><span class="sv" style="color:var(--green);">+₹{t1_pnl:,.0f}</span></div>
                  <div class="sizer-row"><span class="sk">Target 2 P&L</span><span class="sv" style="color:var(--green);">+₹{t2_pnl:,.0f}</span></div>
                </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 1 — SPECIAL SETUPS
# ══════════════════════════════════════════════════════════════════
with tabs[1]:
    col_bb, col_ath = st.columns(2)

    with col_bb:
        st.markdown('<div class="sec">🔥 BB SQUEEZE — EXPLOSIVE MOVE PENDING</div>', unsafe_allow_html=True)
        if bb_sq.empty:
            st.info("No BB squeeze setups detected currently.")
        else:
            st.markdown('<div class="strip-g">Bollinger Band compression detected → price coiling for a breakout. Watch for volume confirmation.</div>', unsafe_allow_html=True)
            for _, r in bb_sq.iterrows():
                sig_c = "g" if r["signal"]=="BUY NOW" else ("a" if r["signal"]=="WATCH" else "r")
                st.markdown(f"""
                <div class="alert-row">
                  <div class="ar-left">
                    <div class="ar-name">🔥 {r['name']} ({r['symbol']})</div>
                    <div class="ar-meta">{r['sector']} · Score {r['score']} · RSI {r['rsi']} · Vol {r['vr']:.1f}x</div>
                  </div>
                  <div class="ar-right">
                    <div class="ar-price">₹{r['ltp']:,.2f}</div>
                    <div class="ar-chg">{regime_pill(r['signal'])}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

    with col_ath:
        st.markdown('<div class="sec">🏔️ NEAR 52-WEEK HIGH — MOMENTUM LEADERS</div>', unsafe_allow_html=True)
        if near_ath.empty:
            st.info("No stocks near their 52-week high currently.")
        else:
            st.markdown('<div class="strip-g">These stocks are trading near annual highs — institutions are holding, momentum is positive.</div>', unsafe_allow_html=True)
            for _, r in near_ath.iterrows():
                chg_val = safe(all_quotes.get(r["symbol"],{}).get("chg"),0)
                chg_c = "sup" if chg_val >= 0 else "sdn"
                st.markdown(f"""
                <div class="alert-row">
                  <div class="ar-left">
                    <div class="ar-name">🏔️ {r['name']} ({r['symbol']})</div>
                    <div class="ar-meta">{r['sector']} · 52W position: {r['w52']:.0f}% · Score {r['score']}</div>
                  </div>
                  <div class="ar-right">
                    <div class="ar-price">₹{r['ltp']:,.2f}</div>
                    <div class="ar-chg {chg_c}">{chg_val:+.2f}% today</div>
                  </div>
                </div>""", unsafe_allow_html=True)

    # ── All alerts / movers ──
    st.markdown('<div class="sec">TODAY\'s TOP MOVERS</div>', unsafe_allow_html=True)
    movers = []
    for sym, q in all_quotes.items():
        if q and "chg" in q:
            info = UNIVERSE.get(sym, {}); chg_v = safe(q.get("chg"),0)
            movers.append({"sym":sym,"name":info.get("name",sym),"sector":info.get("sector",""),
                           "ltp":safe(q.get("last"),0),"chg":chg_v})
    movers_df = pd.DataFrame(movers).sort_values("chg", ascending=False)
    top_g = movers_df.head(5); top_l = movers_df.tail(5)

    mg, ml = st.columns(2)
    with mg:
        st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Top Gainers</div>', unsafe_allow_html=True)
        for _, r in top_g.iterrows():
            st.markdown(f"""
            <div class="alert-row">
              <div class="ar-left">
                <div class="ar-name">{r['name']} ({r['sym']})</div>
                <div class="ar-meta">{r['sector']}</div>
              </div>
              <div class="ar-right">
                <div class="ar-price">₹{r['ltp']:,.2f}</div>
                <div class="ar-chg sup">▲ {r['chg']:.2f}%</div>
              </div>
            </div>""", unsafe_allow_html=True)
    with ml:
        st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Top Losers</div>', unsafe_allow_html=True)
        for _, r in top_l.iterrows():
            st.markdown(f"""
            <div class="alert-row">
              <div class="ar-left">
                <div class="ar-name">{r['name']} ({r['sym']})</div>
                <div class="ar-meta">{r['sector']}</div>
              </div>
              <div class="ar-right">
                <div class="ar-price">₹{r['ltp']:,.2f}</div>
                <div class="ar-chg sdn">▼ {abs(r['chg']):.2f}%</div>
              </div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 2 — NEWS IMPACT
# ══════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="sec">NEWS INTELLIGENCE — MARKET IMPACT ANALYSIS</div>', unsafe_allow_html=True)

    # Bias summary
    bias_col = "var(--green)" if nb["label"]=="POSITIVE" else ("var(--red)" if nb["label"]=="NEGATIVE" else "var(--amber)")
    st.markdown(f"""
    <div style="background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px 20px;margin-bottom:14px;">
      <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
        <div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px;">Overall News Bias</div>
          <div style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;letter-spacing:.06em;color:{bias_col};">{nb['label']}</div>
        </div>
        <div style="flex:1;font-size:.83rem;color:var(--text);line-height:1.7;">
          Score: <b>{nb['score']}</b> · {nb['reason']}<br>
          Positive headlines: <b>{len(nb['top_pos'])}</b> · Negative: <b>{len(nb['top_neg'])}</b>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # News by sector impact
    if not news_all.empty:
        nc1, nc2 = st.columns([1,1])
        with nc1:
            st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.63rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px;">Positive · Market-Moving</div>', unsafe_allow_html=True)
            pos_news = news_all[news_all["score"]>0].head(10)
            for _, r in pos_news.iterrows():
                imp_score = abs(r["score"])
                imp_cls = "high" if imp_score >= 3 else ("med" if imp_score >= 1 else "")
                imp_lbl = ("⚡ HIGH" if imp_score >= 3 else ("📌 MED" if imp_score >= 1 else ""))
                st.markdown(f"""
                <div class="news-item">
                  <div class="ns ns-p">+{r['score']}</div>
                  <div>
                    <div class="nt"><a href="{r['link']}" target="_blank">{r['title'][:105]}</a>
                    {f'<span class="ns-imp {imp_cls}">{imp_lbl}</span>' if imp_lbl else ''}
                    </div>
                    <div class="nm">{r['source']} · {r.get('sector_impact','')[:40]}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        with nc2:
            st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:.63rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px;">Negative · Risk Headlines</div>', unsafe_allow_html=True)
            neg_news = news_all[news_all["score"]<0].head(10)
            for _, r in neg_news.iterrows():
                st.markdown(f"""
                <div class="news-item">
                  <div class="ns ns-n">{r['score']}</div>
                  <div>
                    <div class="nt"><a href="{r['link']}" target="_blank">{r['title'][:105]}</a></div>
                    <div class="nm">{r['source']} · {r.get('sector_impact','')[:40]}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        # Neutral / FYI
        neu_news = news_all[news_all["score"]==0].head(6)
        if not neu_news.empty:
            st.markdown('<div class="sec" style="margin-top:14px;">NEUTRAL / CONTEXT NEWS</div>', unsafe_allow_html=True)
            for _, r in neu_news.iterrows():
                st.markdown(f"""
                <div class="news-item">
                  <div class="ns ns-0">~</div>
                  <div>
                    <div class="nt"><a href="{r['link']}" target="_blank">{r['title'][:110]}</a></div>
                    <div class="nm">{r['source']} · {r.get('sector_impact','')[:40]}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

        # Sector risk matrix
        if any(news_all["sector_impact"].str.len()>0):
            st.markdown('<div class="sec" style="margin-top:14px;">SECTOR NEWS IMPACT MATRIX</div>', unsafe_allow_html=True)
            sector_news_scores = {}
            for _, r in news_all.iterrows():
                tags = r.get("sector_impact","")
                if tags:
                    for tag in tags.split(","):
                        tag = tag.strip()
                        if tag:
                            sector_news_scores.setdefault(tag,[]).append(r["score"])
            if sector_news_scores:
                sn_rows = [{"sector":k,"news_score":round(np.mean(v),1),"headline_count":len(v)}
                           for k,v in sector_news_scores.items()]
                sn_df = pd.DataFrame(sn_rows).sort_values("news_score", ascending=False)
                nc3_cols = st.columns(min(6, len(sn_df)))
                for col, (_, r) in zip(nc3_cols, sn_df.iterrows()):
                    sc_v = r["news_score"]
                    color = "var(--green)" if sc_v > 0 else ("var(--red)" if sc_v < 0 else "var(--muted)")
                    with col:
                        st.markdown(f"""
                        <div class="sec-tile">
                          <div class="sec-tile-name">{r['sector']}</div>
                          <div class="sec-tile-score" style="color:{color};">{sc_v:+.1f}</div>
                          <div class="sec-tile-meta">{r['headline_count']} articles</div>
                        </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 3 — DEEP DIVE
# ══════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="sec">STOCK DEEP DIVE</div>', unsafe_allow_html=True)
    sym_options = [f"{info['name']} ({sym})" for sym,info in UNIVERSE.items()]
    selected = st.selectbox("Choose a stock", sym_options, key="dd_pick")
    dd_sym = selected.split("(")[1].rstrip(")")
    dd_info = UNIVERSE[dd_sym]
    dd_hist = all_hist.get(dd_sym, pd.DataFrame())
    dd_enr  = enrich(dd_hist)
    dd_row  = rank_df[rank_df["symbol"]==dd_sym]

    # Chart
    cfig = candle_chart(dd_hist, dd_enr, dd_sym)
    if cfig: st.plotly_chart(cfig, use_container_width=True, config={"displayModeBar":False})

    if not dd_row.empty:
        r = dd_row.iloc[0]
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            st.metric("Score", f"{r['score']}")
            st.metric("Signal", r["signal"])
            st.metric("Setup", r["setup"])
        with dc2:
            st.metric("RSI 14", f"{r['rsi']}")
            st.metric("Vol Ratio", f"{r['vr']:.1f}x")
            st.metric("52W Position", f"{r['w52']:.0f}%")
        with dc3:
            st.metric("Target 1", f"₹{r['t1']:,.2f} (+{r['pp1']}%)")
            st.metric("Stop Loss", f"₹{r['sl']:,.2f} (-{r['sl_pct']}%)")
            st.metric("R:R Ratio", f"{r['rr']}")

        st.markdown(f"""
        <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:15px 18px;margin-top:10px;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin-bottom:8px;">Why Selected · Intelligence Reason</div>
          <div style="font-size:.85rem;color:var(--text);line-height:1.7;">{r['why']}</div>
          <div style="margin-top:10px;font-size:.8rem;color:var(--muted);">
            Tech: <b style="color:var(--text);">{r['tech']}</b> &nbsp;·&nbsp;
            RS vs NIFTY: <b style="color:var(--text);">{r['rs']}</b> &nbsp;·&nbsp;
            News: <b style="color:var(--text);">{r['news_sc']}</b> &nbsp;·&nbsp;
            Sector: <b style="color:var(--text);">{r['sec_sc']:.0f}</b> &nbsp;·&nbsp;
            OBV: <b style="color:{'var(--green)' if r['obv_pos'] else 'var(--red)'};">{'Positive 🟢' if r['obv_pos'] else 'Negative 🔴'}</b> &nbsp;·&nbsp;
            BB Squeeze: <b style="color:{'var(--green)' if r['bb_squeeze'] else 'var(--muted)'};">{'🔥 YES' if r['bb_squeeze'] else 'No'}</b>
          </div>
        </div>""", unsafe_allow_html=True)

        # Relevant news for this stock
        if not news_all.empty:
            stock_news = news_all[
                news_all["title"].str.contains(dd_sym, case=False, na=False) |
                news_all["title"].str.contains(dd_info["name"].split()[0], case=False, na=False) |
                news_all["sector_impact"].str.contains(dd_info["sector"], case=False, na=False)
            ].head(5)
            if not stock_news.empty:
                st.markdown('<div class="sec" style="margin-top:12px;">RELATED NEWS</div>', unsafe_allow_html=True)
                for _, nr in stock_news.iterrows():
                    cls = "ns-p" if nr["score"]>0 else ("ns-n" if nr["score"]<0 else "ns-0")
                    st.markdown(f"""
                    <div class="news-item">
                      <div class="ns {cls}">{nr['score']:+d}</div>
                      <div>
                        <div class="nt"><a href="{nr['link']}" target="_blank">{nr['title'][:110]}</a></div>
                        <div class="nm">{nr['source']}</div>
                      </div>
                    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 4 — SECTORS
# ══════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown('<div class="sec">SECTOR LEADERSHIP</div>', unsafe_allow_html=True)

    if not sec_agg.empty:
        scols = st.columns(min(5, len(sec_agg)))
        for col, (_, r) in zip(scols, sec_agg.head(5).iterrows()):
            sc_v = r["avg_score"]
            sc_col = "var(--green)" if sc_v >= 65 else ("var(--amber)" if sc_v >= 50 else "var(--red)")
            barcls = "tcbg" if sc_v >= 65 else ("tcba" if sc_v >= 50 else "tcbr")
            with col:
                st.markdown(f"""
                <div class="sec-tile">
                  <div class="sec-tile-name">{r['sector']}</div>
                  <div class="sec-tile-score" style="color:{sc_col};">{sc_v:.1f}</div>
                  {bar(sc_v,barcls)}
                  <div class="sec-tile-meta">BUY NOW: {int(r['buy_count'])} · {int(r['stocks'])} stocks</div>
                </div>""", unsafe_allow_html=True)

        # Sector bar chart
        sf = sector_bar_chart(sec_agg)
        if sf: st.plotly_chart(sf, use_container_width=True, config={"displayModeBar":False})

        # Sector breakdown table
        st.markdown('<div class="sec">ALL SECTOR SCORES</div>', unsafe_allow_html=True)
        for _, r in sec_agg.iterrows():
            sc_v = r["avg_score"]
            sc_col = "var(--green)" if sc_v >= 65 else ("var(--amber)" if sc_v >= 50 else "var(--red)")
            # top stocks in sector
            top_stk = rank_df[rank_df["sector"]==r["sector"]].head(3)["symbol"].tolist()
            st.markdown(f"""
            <div class="alert-row">
              <div class="ar-left">
                <div class="ar-name">{r['sector']}</div>
                <div class="ar-meta">Top: {', '.join(top_stk)} · BUY signals: {int(r['buy_count'])}/{int(r['stocks'])}</div>
              </div>
              <div class="ar-right">
                <div style="font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:{sc_col};">{sc_v:.1f}</div>
                {mini_bar(sc_v,100,sc_col)}
              </div>
            </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 5 — GLOBAL
# ══════════════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="sec">GLOBAL MARKET SNAPSHOT</div>', unsafe_allow_html=True)

    if global_q:
        g_cols = st.columns(len(global_q))
        for col, (name, q) in zip(g_cols, global_q.items()):
            if not q: continue
            chg_v = safe(q.get("chg"),0); last_v = safe(q.get("last"),0)
            gc = "sg" if chg_v >= 0 else "sr"
            with col:
                st.markdown(f"""
                <div class="g-tile {gc}">
                  <div class="g-name">{name}</div>
                  <div class="g-price">{last_v:,.2f}</div>
                  <div class="g-chg {'sup' if chg_v>=0 else 'sdn'}">{'▲' if chg_v>=0 else '▼'} {abs(chg_v):.2f}%</div>
                </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sec" style="margin-top:16px;">GLOBAL IMPACT ANALYSIS</div>', unsafe_allow_html=True)
    impacts = []
    spx_c = safe(global_q.get("S&P 500",{}).get("chg"),0)
    nk_c  = safe(global_q.get("NIKKEI",{}).get("chg"),0)
    hs_c  = safe(global_q.get("HANG SENG",{}).get("chg"),0)
    br_c  = safe(global_q.get("BRENT",{}).get("chg"),0)
    gd_c  = safe(global_q.get("GOLD",{}).get("chg"),0)
    ur_c  = safe(global_q.get("USD/INR",{}).get("chg"),0)

    if spx_c > 0.5: impacts.append(("✅","S&P 500 positive","Positive for IT, Banking, broader market"))
    elif spx_c < -0.5: impacts.append(("⚠️","S&P 500 negative","Negative overhang for IT and export-facing sectors"))
    if br_c > 1.5: impacts.append(("⚠️","Brent rising sharply","Negative for OMCs, Airlines, Consumer; positive for ONGC"))
    elif br_c < -1.0: impacts.append(("✅","Brent easing","Positive for consumer stocks, OMCs, Aviation"))
    if gd_c > 0.5: impacts.append(("✅","Gold up","Risk-off signal — defensive stocks may outperform"))
    if ur_c > 0.3: impacts.append(("⚠️","Rupee weakening","Positive for IT exporters; negative for importers"))
    elif ur_c < -0.3: impacts.append(("✅","Rupee strengthening","Positive for importers; mixed for IT"))
    avg_asia = np.nanmean([nk_c, hs_c])
    if not np.isnan(avg_asia):
        if avg_asia > 0.4: impacts.append(("✅","Asian markets positive","Positive risk sentiment; supports Indian markets"))
        elif avg_asia < -0.4: impacts.append(("⚠️","Asian markets weak","Cautiousness advised; may weigh on open"))

    for icon, title, desc in impacts:
        cls = "strip-g" if icon == "✅" else "strip-r"
        st.markdown(f'<div class="{cls}"><b>{icon} {title}</b> — {desc}</div>', unsafe_allow_html=True)

    if not impacts:
        st.markdown('<div class="strip-a">Global markets mixed — no strong directional signal today.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 6 — FULL SCAN
# ══════════════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="sec">FULL UNIVERSE — ALL 35 STOCKS RANKED</div>', unsafe_allow_html=True)
    disp_cols = ["rank","symbol","name","sector","signal","setup","score","tech",
                 "rs","news_sc","ltp","t1","t2","pp1","pp2","sl","sl_pct","rr",
                 "rsi","vr","donch","w52","bb_squeeze","obv_pos","why"]
    avail = [c for c in disp_cols if c in rank_df.columns]
    st.dataframe(rank_df[avail], use_container_width=True, hide_index=True)
    csv = rank_df[avail].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Full Scan CSV", csv, "marketsense_scan.csv", "text/csv")

    # Quick visual — score distribution
    st.markdown('<div class="sec" style="margin-top:14px;">SCORE DISTRIBUTION</div>', unsafe_allow_html=True)
    fig_dist = go.Figure(go.Bar(
        x=rank_df["symbol"], y=rank_df["score"],
        marker_color=[("#0dffb0" if s>=70 else ("#ffb740" if s>=55 else "#ff3d5a")) for s in rank_df["score"]],
        text=rank_df["score"].round(1), textposition="outside", textfont=dict(size=8),
    ))
    fig_dist.update_layout(**CHART_STYLE, height=250, showlegend=False,
                            xaxis=dict(tickangle=-45, tickfont=dict(size=8)),
                            yaxis=dict(range=[0,100]),
                            margin=dict(l=8,r=8,t=15,b=60))
    st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar":False})

# ──────────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:2.5rem;padding:1rem 0;border-top:1px solid rgba(255,255,255,0.05);
text-align:center;font-family:'JetBrains Mono',monospace;font-size:.64rem;color:#3a4260;">
MARKETSENSE PRO v7 · Probability-based research terminal · NOT financial advice ·
Always apply strict risk management · Past signals do not guarantee future results
</div>""", unsafe_allow_html=True)
