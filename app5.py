# ============================================================
#  MARKETSENSE PRO v6  — Indian Market Intelligence Platform
#  Upgrades: parallel fetch, Plotly charts, FII/DII, PCR,
#  Bollinger squeeze, Piotroski F-Score, heatmap, deep-dive,
#  alert builder, economic calendar, portfolio sizer,
#  breadth chart, sector radar, score history
# ============================================================

import math
import re
import sqlite3
import json
import time as time_module
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup
from streamlit_autorefresh import st_autorefresh

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="MARKETSENSE PRO v6",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
st_autorefresh(interval=900_000, key="ms6_refresh")
IST = ZoneInfo("Asia/Kolkata")

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ============================================================
# UNIVERSE  — M&M fixed to "MM" (yfinance safe ticker)
# ============================================================
SCAN_UNIVERSE = {
    "RELIANCE":   {"name": "Reliance Industries", "sector": "Energy",         "yf": "RELIANCE.NS"},
    "TCS":        {"name": "TCS",                  "sector": "IT",             "yf": "TCS.NS"},
    "INFY":       {"name": "Infosys",              "sector": "IT",             "yf": "INFY.NS"},
    "HCLTECH":    {"name": "HCL Tech",             "sector": "IT",             "yf": "HCLTECH.NS"},
    "WIPRO":      {"name": "Wipro",                "sector": "IT",             "yf": "WIPRO.NS"},
    "TECHM":      {"name": "Tech Mahindra",        "sector": "IT",             "yf": "TECHM.NS"},
    "HDFCBANK":   {"name": "HDFC Bank",            "sector": "Banking",        "yf": "HDFCBANK.NS"},
    "ICICIBANK":  {"name": "ICICI Bank",           "sector": "Banking",        "yf": "ICICIBANK.NS"},
    "AXISBANK":   {"name": "Axis Bank",            "sector": "Banking",        "yf": "AXISBANK.NS"},
    "SBIN":       {"name": "State Bank of India",  "sector": "Banking",        "yf": "SBIN.NS"},
    "KOTAKBANK":  {"name": "Kotak Mahindra Bank",  "sector": "Banking",        "yf": "KOTAKBANK.NS"},
    "INDUSINDBK": {"name": "IndusInd Bank",        "sector": "Banking",        "yf": "INDUSINDBK.NS"},
    "LT":         {"name": "Larsen & Toubro",      "sector": "Infrastructure", "yf": "LT.NS"},
    "RVNL":       {"name": "RVNL",                 "sector": "Infrastructure", "yf": "RVNL.NS"},
    "POWERGRID":  {"name": "Power Grid",           "sector": "Infrastructure", "yf": "POWERGRID.NS"},
    "ADANIPORTS": {"name": "Adani Ports",          "sector": "Infrastructure", "yf": "ADANIPORTS.NS"},
    "NTPC":       {"name": "NTPC",                 "sector": "Energy",         "yf": "NTPC.NS"},
    "TATAPOWER":  {"name": "Tata Power",           "sector": "Energy",         "yf": "TATAPOWER.NS"},
    "COALINDIA":  {"name": "Coal India",           "sector": "Energy",         "yf": "COALINDIA.NS"},
    "BEL":        {"name": "Bharat Electronics",   "sector": "Defence",        "yf": "BEL.NS"},
    "HAL":        {"name": "HAL",                  "sector": "Defence",        "yf": "HAL.NS"},
    "MAZDOCK":    {"name": "Mazagon Dock",         "sector": "Defence",        "yf": "MAZDOCK.NS"},
    "TATAMOTORS": {"name": "Tata Motors",          "sector": "Auto",           "yf": "TATAMOTORS.NS"},
    "MARUTI":     {"name": "Maruti Suzuki",        "sector": "Auto",           "yf": "MARUTI.NS"},
    "MM":         {"name": "Mahindra & Mahindra",  "sector": "Auto",           "yf": "M&M.NS"},
    "EICHERMOT":  {"name": "Eicher Motors",        "sector": "Auto",           "yf": "EICHERMOT.NS"},
    "DIXON":      {"name": "Dixon Technologies",   "sector": "Manufacturing",  "yf": "DIXON.NS"},
    "ULTRACEMCO": {"name": "UltraTech Cement",     "sector": "Materials",      "yf": "ULTRACEMCO.NS"},
    "JSWSTEEL":   {"name": "JSW Steel",            "sector": "Materials",      "yf": "JSWSTEEL.NS"},
    "TATASTEEL":  {"name": "Tata Steel",           "sector": "Materials",      "yf": "TATASTEEL.NS"},
    "GRASIM":     {"name": "Grasim",               "sector": "Materials",      "yf": "GRASIM.NS"},
    "ITC":        {"name": "ITC",                  "sector": "Consumer",       "yf": "ITC.NS"},
    "HINDUNILVR": {"name": "Hindustan Unilever",   "sector": "Consumer",       "yf": "HINDUNILVR.NS"},
    "ASIANPAINT": {"name": "Asian Paints",         "sector": "Consumer",       "yf": "ASIANPAINT.NS"},
    "TITAN":      {"name": "Titan",                "sector": "Consumer",       "yf": "TITAN.NS"},
    "SUNPHARMA":  {"name": "Sun Pharma",           "sector": "Pharma",         "yf": "SUNPHARMA.NS"},
    "BHARTIARTL": {"name": "Bharti Airtel",        "sector": "Telecom",        "yf": "BHARTIARTL.NS"},
    "BAJFINANCE": {"name": "Bajaj Finance",        "sector": "NBFC",           "yf": "BAJFINANCE.NS"},
    "BAJAJFINSV": {"name": "Bajaj Finserv",        "sector": "NBFC",           "yf": "BAJAJFINSV.NS"},
    "GODREJPROP": {"name": "Godrej Properties",    "sector": "Realty",         "yf": "GODREJPROP.NS"},
}

INDEX_TICKERS = {
    "NIFTY 50":   "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "SENSEX":     "^BSESN",
    "INDIA VIX":  "^INDIAVIX",
}
GLOBAL_TICKERS = {
    "S&P 500":  "^GSPC",  "NASDAQ":   "^IXIC",
    "DOW":      "^DJI",   "NIKKEI":   "^N225",
    "HANG SENG":"^HSI",   "SHANGHAI": "000001.SS",
    "BRENT":    "BZ=F",   "WTI":      "CL=F",
    "GOLD":     "GC=F",   "USDINR":   "INR=X",
}

NSE_HOME_URL        = "https://www.nseindia.com/"
NSE_HOLIDAYS_URL    = "https://www.nseindia.com/resources/exchange-communication-holidays"
PIB_RSS_URL         = "https://www.pib.gov.in/rssMain.aspx?reg=3&lang=1"
RBI_PRESS_URL       = "https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx"
WHITEHOUSE_URL      = "https://www.whitehouse.gov/briefing-room/"
GDELT_API           = "https://api.gdeltproject.org/api/v2/doc/doc"
NSE_FII_URL         = "https://www.nseindia.com/api/fiidiiTradeReact"

POSITIVE_WORDS = {
    "ceasefire","cooling","de-escalation","eases","rebound","beats","stimulus",
    "rate cut","liquidity","approval","surge","rally","growth","strong","recover",
    "positive","stable","boost","support","inflow","record order","wins order",
    "expansion","upgrade","soft landing","fall in oil","order win",
    "guidance raised","outperform","breakout","all-time high","record high",
    "earnings beat","strong results","robust","profit rise","capex boost",
}
NEGATIVE_WORDS = {
    "war","tariff","sanction","inflation","spike","selloff","fall","crash",
    "downgrade","tightening","volatility","ban","concern","fear","outflow",
    "conflict","disruption","weak","uncertain","lawsuit","fragile","shortage",
    "misses","cuts guidance","hot inflation","oil spike","rate hike","profit warning",
    "default","bubble","probe","investigation","collapse","panic","recession",
    "stagflation","geopolitical","escalation","slowdown",
}
SECTOR_KEYWORDS = {
    "Banking":        ["rbi","repo","bank","liquidity","rupee","credit","npa","slippage"],
    "IT":             ["ai","tech","software","cloud","nasdaq","it sector","digital","cybersecurity"],
    "Energy":         ["oil","crude","brent","wti","gas","hormuz","opec","energy"],
    "Defence":        ["defence","military","war","border","drdo","fighter"],
    "Infrastructure": ["capex","infrastructure","rail","road","power","construction","smart city"],
    "Consumer":       ["inflation","consumption","retail","demand","fmcg","gst","festival"],
    "Materials":      ["metal","steel","aluminium","copper","commodity","cement","iron ore"],
    "Auto":           ["auto","vehicle","car","ev","electric","tractor","two-wheeler"],
    "Pharma":         ["drug","pharma","healthcare","usfda","api","biotech","clinical"],
    "Telecom":        ["telecom","5g","spectrum","jio","airtel"],
    "NBFC":           ["credit","finance","loan","rate","microfinance","housing finance"],
    "Realty":         ["property","real estate","housing","residential","commercial","reit"],
    "Manufacturing":  ["manufacturing","electronics","pli","semiconductor","make in india"],
}

# Economic calendar — static but rich
ECONOMIC_CALENDAR = [
    {"event": "RBI MPC Decision",          "date": "2025-06-06", "impact": "HIGH",   "sector": "Banking,NBFC"},
    {"event": "India CPI Inflation",        "date": "2025-05-12", "impact": "HIGH",   "sector": "Consumer,Banking"},
    {"event": "India IIP Data",             "date": "2025-05-12", "impact": "MEDIUM", "sector": "Manufacturing,Materials"},
    {"event": "India GDP Q4",               "date": "2025-05-30", "impact": "HIGH",   "sector": "All"},
    {"event": "US Fed FOMC Meeting",        "date": "2025-05-07", "impact": "HIGH",   "sector": "Banking,IT"},
    {"event": "US CPI Data",               "date": "2025-05-13", "impact": "HIGH",   "sector": "All"},
    {"event": "India WPI Inflation",        "date": "2025-05-14", "impact": "MEDIUM", "sector": "Materials,Consumer"},
    {"event": "NSE F&O Expiry (Monthly)",   "date": "2025-05-29", "impact": "MEDIUM", "sector": "All"},
    {"event": "NSE F&O Expiry (Weekly)",    "date": "2025-05-08", "impact": "LOW",    "sector": "All"},
    {"event": "NSE F&O Expiry (Weekly)",    "date": "2025-05-15", "impact": "LOW",    "sector": "All"},
    {"event": "NSE F&O Expiry (Weekly)",    "date": "2025-05-22", "impact": "LOW",    "sector": "All"},
    {"event": "US NFP Jobs Report",         "date": "2025-05-02", "impact": "HIGH",   "sector": "IT,Banking"},
    {"event": "Brent OPEC Meeting",         "date": "2025-06-01", "impact": "HIGH",   "sector": "Energy"},
    {"event": "India Foreign Trade Data",   "date": "2025-05-15", "impact": "MEDIUM", "sector": "All"},
    {"event": "RBI Monetary Policy Report", "date": "2025-05-20", "impact": "MEDIUM", "sector": "Banking"},
]

# ============================================================
# DB — score history (SQLite in /tmp for Streamlit Cloud)
# ============================================================
DB_PATH = "/tmp/marketsense_history.db"

def init_db():
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("""
            CREATE TABLE IF NOT EXISTS score_history (
                date TEXT, symbol TEXT, score REAL, signal TEXT,
                ltp REAL, tech_score REAL, rs_score REAL,
                PRIMARY KEY (date, symbol)
            )
        """)
        con.commit(); con.close()
    except Exception:
        pass

def save_scores(rank_df: pd.DataFrame):
    try:
        today = datetime.now(IST).strftime("%Y-%m-%d")
        con = sqlite3.connect(DB_PATH)
        for _, r in rank_df.iterrows():
            con.execute("""
                INSERT OR REPLACE INTO score_history
                (date,symbol,score,signal,ltp,tech_score,rs_score)
                VALUES (?,?,?,?,?,?,?)
            """, (today, r["symbol"], r["score"], r["signal"],
                  r["ltp"], r["tech_score"], r["rs_score"]))
        con.commit(); con.close()
    except Exception:
        pass

def load_score_history(symbol: str) -> pd.DataFrame:
    try:
        con = sqlite3.connect(DB_PATH)
        df = pd.read_sql(
            "SELECT date,score,signal,ltp FROM score_history WHERE symbol=? ORDER BY date",
            con, params=(symbol,))
        con.close()
        return df
    except Exception:
        return pd.DataFrame()

init_db()

# ============================================================
# CSS / THEME
# ============================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@700;800;900&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#08090d; --bg2:#0c0e15; --panel:#10131c; --border:rgba(255,255,255,0.07);
  --border2:rgba(255,255,255,0.13); --text:#e4e8f5; --muted:#7a84a0; --muted2:#4d5470;
  --green:#00ffa3; --green2:#00c97a; --red:#ff4757; --red2:#cc2233;
  --amber:#ffd166; --amber2:#e6a800; --blue:#4ea8ff; --cyan:#00e5ff;
  --purple:#a78bfa; --glow:0 0 30px rgba(0,255,163,0.15);
  --shadow:0 20px 60px rgba(0,0,0,0.6);
}
.stApp { background:var(--bg); font-family:'DM Sans',sans-serif; }
.stApp::before {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background:
    radial-gradient(ellipse 60% 40% at 10% 0%,rgba(0,255,163,0.06),transparent 60%),
    radial-gradient(ellipse 50% 60% at 90% 100%,rgba(78,168,255,0.07),transparent 60%);
}
.block-container { max-width:1380px!important; padding:1rem 1.25rem 3rem!important; position:relative; z-index:1; }
h1,h2,h3,h4,h5,h6,p,span,div,label,li { color:var(--text); }
* { box-sizing:border-box; }

/* sidebar */
[data-testid="stSidebar"] { width:275px!important; min-width:275px!important; background:#0a0c13!important; border-right:1px solid var(--border); }
[data-testid="stSidebar"]::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg,var(--green),var(--blue),var(--purple)); }
[data-testid="stSidebar"] * { color:#c8d0e8!important; }

/* topbar */
.ms-topbar { display:flex; align-items:center; justify-content:space-between; padding:1rem 1.5rem; background:rgba(16,19,28,0.85); border:1px solid var(--border); border-radius:16px; margin-bottom:14px; backdrop-filter:blur(12px); }
.ms-logo { font-family:'Syne',sans-serif; font-size:1.5rem; font-weight:900; letter-spacing:-0.04em; background:linear-gradient(110deg,var(--green) 0%,var(--cyan) 60%,var(--blue) 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.ms-meta { font-family:'Space Mono',monospace; font-size:.7rem; color:var(--muted); text-align:right; line-height:1.7; }
.ms-meta b { color:var(--text); }

/* pills */
.pill { display:inline-flex; align-items:center; gap:5px; padding:.28rem .72rem; border-radius:999px; font-family:'Space Mono',monospace; font-size:.68rem; font-weight:700; letter-spacing:.05em; border:1px solid; text-transform:uppercase; }
.pill::before { content:'●'; font-size:.45rem; }
.pill-green  { background:rgba(0,255,163,0.1);  color:var(--green);  border-color:rgba(0,255,163,0.25); }
.pill-red    { background:rgba(255,71,87,0.1);   color:var(--red);    border-color:rgba(255,71,87,0.25); }
.pill-amber  { background:rgba(255,209,102,0.1); color:var(--amber);  border-color:rgba(255,209,102,0.25); }
.pill-blue   { background:rgba(78,168,255,0.1);  color:var(--blue);   border-color:rgba(78,168,255,0.25); }
.pill-purple { background:rgba(167,139,250,0.1); color:var(--purple); border-color:rgba(167,139,250,0.25); }

/* stat strip */
.stat-strip { display:grid; grid-template-columns:repeat(6,1fr); gap:10px; margin-bottom:14px; }
.stat-cell { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:13px 15px; position:relative; overflow:hidden; }
.stat-cell::after { content:''; position:absolute; top:0; left:0; right:0; height:2px; }
.stat-cell.green::after { background:linear-gradient(90deg,var(--green),transparent); }
.stat-cell.red::after   { background:linear-gradient(90deg,var(--red),transparent); }
.stat-cell.amber::after { background:linear-gradient(90deg,var(--amber),transparent); }
.stat-cell.blue::after  { background:linear-gradient(90deg,var(--blue),transparent); }
.stat-label { font-family:'Space Mono',monospace; font-size:.6rem; color:var(--muted); letter-spacing:.08em; text-transform:uppercase; margin-bottom:5px; }
.stat-val   { font-family:'Syne',sans-serif; font-size:1.4rem; font-weight:800; color:white; line-height:1; }
.stat-sub   { font-size:.75rem; color:var(--muted); margin-top:4px; }
.stat-sub.up { color:var(--green); } .stat-sub.dn { color:var(--red); }

/* context grid */
.ctx-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px; }
.ctx-card { background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:16px 18px; }
.ctx-title { font-family:'Space Mono',monospace; font-size:.63rem; color:var(--muted); letter-spacing:.1em; text-transform:uppercase; margin-bottom:9px; }
.ctx-body  { font-size:.87rem; line-height:1.65; color:var(--text); }
.ctx-body b { color:white; }

/* section title */
.sec-title { font-family:'Syne',sans-serif; font-size:1rem; font-weight:800; color:white; letter-spacing:-0.02em; margin:16px 0 10px; display:flex; align-items:center; gap:8px; }
.sec-title::before { content:''; display:inline-block; width:3px; height:16px; border-radius:2px; background:linear-gradient(180deg,var(--green),var(--blue)); }

/* idea cards */
.idea-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:13px; }
.idea-card { background:var(--panel); border:1px solid var(--border); border-radius:18px; padding:17px; position:relative; overflow:hidden; transition:transform .2s,border-color .2s,box-shadow .2s; min-height:295px; }
.idea-card:hover { transform:translateY(-3px); border-color:var(--border2); box-shadow:var(--shadow),var(--glow); }
.idea-card::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; }
.idea-card.buy::before   { background:linear-gradient(90deg,var(--green),var(--cyan)); }
.idea-card.watch::before { background:linear-gradient(90deg,var(--amber),var(--blue)); }
.idea-card.skip::before  { background:linear-gradient(90deg,var(--red),transparent); }
.card-ticker { font-family:'Space Mono',monospace; font-size:.7rem; color:var(--muted); letter-spacing:.12em; margin-bottom:3px; }
.card-name   { font-family:'Syne',sans-serif; font-size:1rem; font-weight:800; color:white; line-height:1.2; }
.card-sector { font-size:.76rem; color:var(--muted); margin-top:2px; }
.card-signal { font-family:'Space Mono',monospace; font-size:.9rem; font-weight:700; margin:10px 0 3px; }
.card-signal.buy   { color:var(--green); }
.card-signal.watch { color:var(--amber); }
.card-signal.skip  { color:var(--red); }
.card-badge { display:inline-block; padding:2px 9px; border-radius:999px; font-size:.68rem; font-weight:700; font-family:'Space Mono',monospace; background:rgba(255,255,255,0.06); color:var(--muted); margin-bottom:10px; }
.bar { height:4px; border-radius:999px; background:rgba(255,255,255,0.07); overflow:hidden; margin-bottom:8px; }
.bar-fill { height:100%; border-radius:999px; }
.bar-fill.green { background:linear-gradient(90deg,var(--green2),var(--green)); }
.bar-fill.amber { background:linear-gradient(90deg,var(--amber2),var(--amber)); }
.bar-fill.red   { background:linear-gradient(90deg,var(--red2),var(--red)); }
.card-row { display:flex; justify-content:space-between; font-size:.8rem; padding:3px 0; border-bottom:1px solid rgba(255,255,255,0.04); }
.card-row .k { color:var(--muted); } .card-row .v { color:white; font-weight:600; }
.card-row .v.up { color:var(--green); } .card-row .v.dn { color:var(--red); }
.card-why { margin-top:9px; font-size:.74rem; color:var(--muted); line-height:1.5; border-top:1px solid rgba(255,255,255,0.05); padding-top:7px; }

/* index / global tiles */
.index-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:11px; }
.index-tile { background:var(--panel); border:1px solid var(--border); border-radius:13px; padding:15px; transition:border-color .2s; }
.index-tile:hover { border-color:var(--border2); }
.index-name  { font-family:'Space Mono',monospace; font-size:.63rem; color:var(--muted); letter-spacing:.1em; text-transform:uppercase; margin-bottom:7px; }
.index-price { font-family:'Syne',sans-serif; font-size:1.25rem; font-weight:800; color:white; }
.index-chg   { font-size:.8rem; font-weight:600; margin-top:3px; }
.index-chg.up { color:var(--green); } .index-chg.dn { color:var(--red); }
.index-extra  { font-size:.72rem; color:var(--muted); margin-top:2px; }

/* sector cards */
.sector-board { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; }
.sector-card  { background:var(--panel); border:1px solid var(--border); border-radius:13px; padding:13px 15px; }
.sector-name  { font-family:'Syne',sans-serif; font-size:.92rem; font-weight:800; color:white; margin-bottom:5px; }
.sector-score-display { font-family:'Space Mono',monospace; font-size:1.4rem; font-weight:700; }
.sector-meta  { font-size:.73rem; color:var(--muted); margin-top:5px; }

/* news */
.news-row { display:flex; align-items:flex-start; gap:13px; padding:9px 0; border-bottom:1px solid rgba(255,255,255,0.05); }
.news-score { min-width:30px; height:30px; border-radius:7px; display:flex; align-items:center; justify-content:center; font-family:'Space Mono',monospace; font-size:.7rem; font-weight:700; }
.ns-pos { background:rgba(0,255,163,0.12); color:var(--green); }
.ns-neg { background:rgba(255,71,87,0.12); color:var(--red); }
.ns-neu { background:rgba(255,255,255,0.06); color:var(--muted); }
.news-title { font-size:.83rem; color:var(--text); line-height:1.4; }
.news-meta  { font-size:.7rem; color:var(--muted2); margin-top:2px; }

/* alert / calendar cards */
.alert-card { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:12px 15px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; }
.cal-row { display:flex; align-items:center; gap:14px; padding:10px 0; border-bottom:1px solid rgba(255,255,255,0.05); }
.cal-date { font-family:'Space Mono',monospace; font-size:.7rem; color:var(--muted); min-width:80px; }
.cal-event { font-size:.86rem; color:var(--text); }
.cal-impact-HIGH   { color:var(--red);   font-size:.68rem; font-weight:700; }
.cal-impact-MEDIUM { color:var(--amber); font-size:.68rem; font-weight:700; }
.cal-impact-LOW    { color:var(--muted); font-size:.68rem; font-weight:700; }

/* sizer */
.sizer-card { background:var(--panel); border:1px solid var(--border); border-radius:15px; padding:18px 20px; }
.sizer-title { font-family:'Syne',sans-serif; font-size:.95rem; font-weight:800; color:white; margin-bottom:12px; }
.sizer-row { display:flex; justify-content:space-between; padding:5px 0; border-bottom:1px solid rgba(255,255,255,0.04); font-size:.84rem; }
.sizer-row .sk { color:var(--muted); } .sizer-row .sv { color:white; font-weight:600; font-family:'Space Mono',monospace; }
.sizer-row .sv.big { color:var(--green); font-size:1.15rem; font-family:'Syne',sans-serif; font-weight:900; }

/* regime meter */
.regime-meter { display:flex; align-items:center; gap:14px; background:var(--panel); border:1px solid var(--border); border-radius:13px; padding:13px 17px; margin-bottom:14px; }
.regime-bar  { flex:1; height:7px; background:rgba(255,255,255,0.07); border-radius:999px; overflow:hidden; }
.regime-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,var(--green2),var(--green),var(--cyan)); }
.regime-score { font-family:'Space Mono',monospace; font-size:.8rem; color:var(--muted); white-space:nowrap; }

/* strips */
.warn-strip  { background:rgba(255,71,87,0.08);   border:1px solid rgba(255,71,87,0.2);   border-radius:10px; padding:10px 15px; font-size:.82rem; color:#fca5a5; margin-bottom:10px; }
.info-strip  { background:rgba(78,168,255,0.08);  border:1px solid rgba(78,168,255,0.2);  border-radius:10px; padding:10px 15px; font-size:.82rem; color:#93c5fd; margin-bottom:6px; }
.good-strip  { background:rgba(0,255,163,0.07);   border:1px solid rgba(0,255,163,0.2);   border-radius:10px; padding:10px 15px; font-size:.82rem; color:#6ee7b7; margin-bottom:10px; }
.amber-strip { background:rgba(255,209,102,0.08); border:1px solid rgba(255,209,102,0.2); border-radius:10px; padding:10px 15px; font-size:.82rem; color:#fde68a; margin-bottom:6px; }

/* tabs */
.stTabs [data-baseweb="tab-list"] { gap:5px; flex-wrap:nowrap!important; overflow-x:auto; background:transparent!important; border-bottom:1px solid var(--border)!important; padding-bottom:0; }
.stTabs [data-baseweb="tab"] { font-family:'Space Mono',monospace!important; font-size:.68rem!important; letter-spacing:.05em; text-transform:uppercase!important; background:transparent!important; border:none!important; border-radius:0!important; color:var(--muted)!important; padding:9px 14px!important; border-bottom:2px solid transparent!important; white-space:nowrap; }
[aria-selected="true"] { color:var(--green)!important; border-bottom:2px solid var(--green)!important; }

/* dataframes */
[data-testid="stDataFrame"] { border:1px solid var(--border)!important; border-radius:11px!important; overflow:hidden; }
[data-testid="stDataFrame"] * { font-family:'Space Mono',monospace!important; font-size:.73rem!important; }

/* piotroski badge */
.fscore-badge { display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:50%; font-family:'Space Mono',monospace; font-size:.8rem; font-weight:700; }
.fscore-hi { background:rgba(0,255,163,0.15); color:var(--green); border:1px solid rgba(0,255,163,0.3); }
.fscore-md { background:rgba(255,209,102,0.15); color:var(--amber); border:1px solid rgba(255,209,102,0.3); }
.fscore-lo { background:rgba(255,71,87,0.15); color:var(--red); border:1px solid rgba(255,71,87,0.3); }

/* fii dii */
.flow-card { background:var(--panel); border:1px solid var(--border); border-radius:12px; padding:14px 16px; }
.flow-label { font-family:'Space Mono',monospace; font-size:.63rem; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px; }
.flow-val   { font-family:'Syne',sans-serif; font-size:1.25rem; font-weight:800; }
.flow-val.pos { color:var(--green); } .flow-val.neg { color:var(--red); }

/* responsive */
@media(max-width:1100px) { .stat-strip{grid-template-columns:repeat(3,1fr);} .idea-grid{grid-template-columns:repeat(2,1fr);} .index-grid{grid-template-columns:repeat(2,1fr);} .sector-board{grid-template-columns:repeat(2,1fr);} }
@media(max-width:640px)  { .stat-strip{grid-template-columns:repeat(2,1fr);} .idea-grid,.index-grid,.sector-board{grid-template-columns:1fr;} .ctx-grid{grid-template-columns:1fr;} }
</style>
""", unsafe_allow_html=True)

# ============================================================
# MATH HELPERS
# ============================================================
def sf(v, default=np.nan):
    try: return float(v)
    except: return default

def pct_chg(cur, prev):
    if prev in [0, None] or pd.isna(prev) or pd.isna(cur): return np.nan
    return ((cur/prev)-1)*100

def clean_ohlcv(df):
    if df is None or df.empty: return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        if len(set(df.columns.get_level_values(0)))==1: df.columns=df.columns.get_level_values(1)
        elif len(set(df.columns.get_level_values(1)))==1: df.columns=df.columns.get_level_values(0)
    cols=[c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
    return df[cols].copy().dropna(subset=["Close"])

# ── Indicators ──────────────────────────────────────────────
def calc_rsi(s, p=14):
    d=s.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    ag=g.ewm(alpha=1/p,min_periods=p,adjust=False).mean()
    al=l.ewm(alpha=1/p,min_periods=p,adjust=False).mean()
    return 100-(100/(1+ag/al.replace(0,np.nan)))

def calc_macd(s,fast=12,slow=26,sig=9):
    ef=s.ewm(span=fast,adjust=False).mean(); es=s.ewm(span=slow,adjust=False).mean()
    line=ef-es; signal=line.ewm(span=sig,adjust=False).mean()
    return line,signal,line-signal

def calc_atr(df,p=14):
    hl=df["High"]-df["Low"]
    hc=(df["High"]-df["Close"].shift()).abs()
    lc=(df["Low"]-df["Close"].shift()).abs()
    return pd.concat([hl,hc,lc],axis=1).max(axis=1).rolling(p).mean()

def calc_stoch_rsi(s,p=14,k=3):
    r=calc_rsi(s,p); mn=r.rolling(p).min(); mx=r.rolling(p).max()
    return ((r-mn)/(mx-mn+1e-9)*100).rolling(k).mean()

def calc_williams_r(df,p=14):
    h=df["High"].rolling(p).max(); l=df["Low"].rolling(p).min()
    return -100*(h-df["Close"])/(h-l+1e-9)

def calc_obv(df):
    return (np.sign(df["Close"].diff()).fillna(0)*df["Volume"]).cumsum()

def calc_vwap_dev(df,p=20):
    typ=(df["High"]+df["Low"]+df["Close"])/3
    vwap=(typ*df["Volume"]).rolling(p).sum()/df["Volume"].rolling(p).sum()
    return ((df["Close"]-vwap)/vwap)*100

def calc_donchian(df,p=20):
    return ((df["Close"]-df["Low"].rolling(p).min())/(df["High"].rolling(p).max()-df["Low"].rolling(p).min()+1e-9))*100

def calc_bollinger(s,p=20,std=2):
    mid=s.rolling(p).mean(); sd=s.rolling(p).std()
    return mid+std*sd, mid, mid-std*sd

def calc_bb_squeeze(df,p=20):
    """Bollinger Band width — low = compression before breakout."""
    _,mid,_ = calc_bollinger(df["Close"],p)
    sd=df["Close"].rolling(p).std()
    return sd/mid*100   # BB%width

def enrich(df):
    if df is None or df.empty or len(df) < 100: return pd.DataFrame()
    x=df.copy()
    for sp in [9,20,50,100,200]: x[f"EMA{sp}"]=x["Close"].ewm(span=sp,adjust=False).mean()
    x["SMA50"]=x["Close"].rolling(50).mean()
    x["RSI14"]=calc_rsi(x["Close"],14); x["RSI7"]=calc_rsi(x["Close"],7)
    x["StochRSI"]=calc_stoch_rsi(x["Close"])
    x["WilliamsR"]=calc_williams_r(x,14)
    x["ATR14"]=calc_atr(x,14); x["ATR7"]=calc_atr(x,7)
    x["OBV"]=calc_obv(x); x["OBV_EMA"]=x["OBV"].ewm(span=20,adjust=False).mean()
    x["VWAP_DEV"]=calc_vwap_dev(x,20)
    x["DONCH20"]=calc_donchian(x,20)
    x["BB_UPPER"],x["BB_MID"],x["BB_LOWER"]=calc_bollinger(x["Close"])
    x["BB_SQUEEZE"]=calc_bb_squeeze(x)
    x["BB_SQUEEZE_AVG"]=x["BB_SQUEEZE"].rolling(50).mean()
    x["VOL20"]=x["Volume"].rolling(20).mean(); x["VOL10"]=x["Volume"].rolling(10).mean()
    x["VOL_RATIO"]=x["Volume"]/x["VOL20"]; x["VOL_RATIO10"]=x["Volume"]/x["VOL10"]
    x["HH20"]=x["High"].rolling(20).max(); x["LL20"]=x["Low"].rolling(20).min()
    x["HH50"]=x["High"].rolling(50).max(); x["LL50"]=x["Low"].rolling(50).min()
    x["HH10"]=x["High"].rolling(10).max()
    for p in [1,3,5,10,20,60]: x[f"RET_{p}D"]=x["Close"].pct_change(p)
    ml,ms,mh=calc_macd(x["Close"]); x["MACD"]=ml; x["MACD_SIGNAL"]=ms; x["MACD_HIST"]=mh
    x["EMA20_SLOPE"]=x["EMA20"].diff(5)/x["Close"]*100
    x["52W_HIGH"]=x["High"].rolling(252).max(); x["52W_LOW"]=x["Low"].rolling(252).min()
    x["52W_PCT"]=(x["Close"]-x["52W_LOW"])/(x["52W_HIGH"]-x["52W_LOW"]+1e-9)*100
    return x.dropna()

def classify_setup(d):
    close_=sf(d.get("Close")); hh20=sf(d.get("HH20")); ema20=sf(d.get("EMA20"))
    ema50=sf(d.get("EMA50")); rsi_=sf(d.get("RSI14")); sr=sf(d.get("StochRSI"))
    vr=sf(d.get("VOL_RATIO"),1); ret5=sf(d.get("RET_5D")); donch=sf(d.get("DONCH20"))
    bbs=sf(d.get("BB_SQUEEZE")); bbsa=sf(d.get("BB_SQUEEZE_AVG"))
    if bbs < bbsa*0.85 and rsi_ > 50: return "BB Squeeze Breakout"
    if close_ >= 0.99*hh20 and rsi_ >= 58 and vr >= 1.4: return "Volume Breakout"
    if close_ >= 0.99*hh20 and rsi_ >= 58: return "Breakout"
    if donch >= 85 and rsi_ >= 65: return "Momentum Surge"
    if close_ > ema20 > ema50 and -0.04 <= ret5 <= 0.015 and sr <= 45: return "EMA Pullback"
    if close_ >= ema50 and 35 <= rsi_ <= 50 and sr <= 30: return "Oversold Bounce"
    if close_ > ema20 and sr <= 20: return "StochRSI Reset"
    return "Trend"

# ============================================================
# DATA FETCH — PARALLEL
# ============================================================
@st.cache_data(ttl=300)
def fetch_hist(symbol, period="1y", interval="1d"):
    try:
        df=yf.download(symbol,period=period,interval=interval,
                       auto_adjust=True,progress=False,threads=False)
        return clean_ohlcv(df)
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_quote(symbol):
    df=fetch_hist(symbol,period="10d")
    if df.empty or len(df)<2: return {}
    last=sf(df["Close"].iloc[-1]); prev=sf(df["Close"].iloc[-2])
    return {"last":last,"prev":prev,"chg_pct":pct_chg(last,prev)}

def parallel_fetch_universe(universe):
    """Fetch all OHLCV data in parallel using ThreadPoolExecutor."""
    results = {}
    def _fetch(sym, yf_sym):
        return sym, fetch_hist(yf_sym, period="1y")
    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(_fetch, sym, info["yf"]): sym
                   for sym, info in universe.items()}
        for f in as_completed(futures):
            sym, df = f.result()
            results[sym] = df
    return results

def parallel_fetch_fundamentals(universe):
    """Fetch fundamentals for all stocks in parallel."""
    results = {}
    def _fetch(sym):
        return sym, fetch_fundamentals(sym, universe[sym]["yf"])
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_fetch, sym): sym for sym in universe}
        for f in as_completed(futures):
            sym, fund = f.result()
            results[sym] = fund
    return results

@st.cache_data(ttl=3600)
def fetch_fundamentals(symbol, yf_sym):
    out = {
        "symbol":symbol,"market_cap":np.nan,"trailing_pe":np.nan,"forward_pe":np.nan,
        "peg_ratio":np.nan,"price_to_book":np.nan,"debt_to_equity":np.nan,
        "roe":np.nan,"profit_margin":np.nan,"revenue_growth":np.nan,
        "earnings_growth":np.nan,"current_ratio":np.nan,"quick_ratio":np.nan,
        "next_earnings_date":None,"recent_perf_score":50,
        "recent_perf_notes":"limited data","has_data":False,
        "f_score":0,"f_score_detail":{},
    }
    try:
        tk=yf.Ticker(yf_sym)
        info={}
        try: info=tk.info or {}
        except: info={}
        for k,f in [("market_cap","marketCap"),("trailing_pe","trailingPE"),
                    ("forward_pe","forwardPE"),("peg_ratio","pegRatio"),
                    ("price_to_book","priceToBook"),("debt_to_equity","debtToEquity"),
                    ("roe","returnOnEquity"),("profit_margin","profitMargins"),
                    ("revenue_growth","revenueGrowth"),("earnings_growth","earningsGrowth"),
                    ("current_ratio","currentRatio"),("quick_ratio","quickRatio")]:
            out[k]=info.get(f,np.nan)
        try:
            cal=tk.calendar
            if isinstance(cal,dict):
                dt=cal.get("Earnings Date")
                out["next_earnings_date"]=dt[0] if isinstance(dt,(list,tuple)) and len(dt)>0 else dt
            elif hasattr(cal,"iloc") and len(cal)>0 and "Earnings Date" in cal.index:
                out["next_earnings_date"]=cal.loc["Earnings Date"].values[0]
        except: pass
        # quarterly
        score=50; notes=[]
        try:
            qf=tk.quarterly_financials
            if not qf.empty:
                def find_m(df,cands):
                    for idx in df.index:
                        low=str(idx).lower()
                        if any(c in low for c in cands): return df.loc[idx]
                    return None
                rev=find_m(qf,["total revenue","revenue"])
                ni =find_m(qf,["net income","netincome"])
                op =find_m(qf,["operating income","ebit"])
                if rev is not None:
                    rv=pd.to_numeric(rev,errors="coerce").dropna().values[:4]
                    if len(rv)>=2:
                        if rv[0]>rv[1]: score+=8; notes.append("revenue↑")
                        else: score-=6; notes.append("revenue↓")
                if ni is not None:
                    nv=pd.to_numeric(ni,errors="coerce").dropna().values[:4]
                    if len(nv)>=2:
                        if nv[0]>nv[1]: score+=12; notes.append("profit↑")
                        else: score-=10; notes.append("profit↓")
                    if len(nv)>=5:
                        yoy=(nv[0]-nv[4])/abs(nv[4]) if nv[4]!=0 else 0
                        if yoy>0.15: score+=8; notes.append(f"YoY+{yoy*100:.0f}%")
                        elif yoy<-0.15: score-=8
                if rev is not None and op is not None:
                    rv2=pd.to_numeric(rev,errors="coerce").dropna().values[:2]
                    ov=pd.to_numeric(op,errors="coerce").dropna().values[:2]
                    if len(rv2)>=2 and len(ov)>=2 and rv2[0]!=0 and rv2[1]!=0:
                        if ov[0]/rv2[0]>ov[1]/rv2[1]: score+=6; notes.append("margins↑")
                        else: score-=4; notes.append("margins↓")
        except: pass
        # Piotroski F-Score (simplified from available yf data)
        fs={}; ftotal=0
        roe=sf(out["roe"]); cf=sf(info.get("operatingCashflow",np.nan))
        de=sf(out["debt_to_equity"]); cr=sf(out["current_ratio"])
        rg=sf(out["revenue_growth"]); eg=sf(out["earnings_growth"])
        pm=sf(out["profit_margin"])
        if not np.isnan(roe) and roe>0:       fs["ROE+"]     =1; ftotal+=1
        if not np.isnan(cf) and cf>0:         fs["CFO+"]     =1; ftotal+=1
        if not np.isnan(eg) and eg>0:         fs["∆ROA+"]    =1; ftotal+=1
        if not np.isnan(cf) and not np.isnan(roe) and cf>roe: fs["CFO>ROA"]=1; ftotal+=1
        if not np.isnan(de) and de<1.0:       fs["Debt↓"]    =1; ftotal+=1
        if not np.isnan(cr) and cr>1.2:       fs["Liquid+"]  =1; ftotal+=1
        if not np.isnan(rg) and rg>0.05:      fs["Rev↑"]     =1; ftotal+=1
        if not np.isnan(pm) and pm>0.08:      fs["Margin↑"]  =1; ftotal+=1
        if not np.isnan(eg) and eg>0.10:      fs["EPS↑"]     =1; ftotal+=1
        out["recent_perf_score"]=max(0,min(100,score))
        out["recent_perf_notes"]=", ".join(notes[:4]) if notes else out["recent_perf_notes"]
        out["f_score"]=ftotal; out["f_score_detail"]=fs; out["has_data"]=True
    except: pass
    return out

@st.cache_data(ttl=21600)
def fetch_holidays(year=None):
    target=year or datetime.now(IST).year; rows=[]
    try:
        r=requests.get(NSE_HOLIDAYS_URL,headers=REQUEST_HEADERS,timeout=20); r.raise_for_status()
        text=BeautifulSoup(r.text,"html.parser").get_text("\n",strip=True)
        for dt_s,desc in re.findall(r"\d+,\s+(\d{1,2}-[A-Za-z]{3}-\d{4}),\s+[A-Za-z]+,\s+(.+)",text):
            try:
                dt=pd.to_datetime(dt_s,format="%d-%b-%Y").date()
                if dt.year==target: rows.append({"date":dt,"holiday":desc.strip()})
            except: pass
    except: pass
    return pd.DataFrame(rows).drop_duplicates()

@st.cache_data(ttl=900)
def fetch_breadth():
    try:
        s=requests.Session(); s.headers.update(REQUEST_HEADERS)
        s.get(NSE_HOME_URL,timeout=20)
        r=s.get(NSE_HOME_URL,timeout=20); r.raise_for_status()
        text=BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True)
        ma=re.search(r"Advances\s+(\d[\d,]*)",text,re.I)
        md=re.search(r"Declines\s+(\d[\d,]*)",text,re.I)
        mu=re.search(r"Unchanged\s+(\d[\d,]*)",text,re.I)
        if ma and md:
            adv=int(ma.group(1).replace(",","")); dec=int(md.group(1).replace(",",""))
            unch=int(mu.group(1).replace(",","")) if mu else 0; total=adv+dec+unch
            return {"source":"NSE official","advances":adv,"declines":dec,"unchanged":unch,
                    "adv_pct":round(adv/total*100,2) if total else 50,"total":total}
    except: pass
    return {}

@st.cache_data(ttl=900)
def fetch_fii_dii():
    """Fetch FII/DII data from NSE API."""
    try:
        s=requests.Session(); s.headers.update(REQUEST_HEADERS)
        s.get(NSE_HOME_URL,timeout=15)
        r=s.get(NSE_FII_URL,headers={**REQUEST_HEADERS,"Referer":NSE_HOME_URL},timeout=15)
        r.raise_for_status(); data=r.json()
        if isinstance(data,list) and len(data)>0:
            latest=data[0]
            return {
                "date":     latest.get("date","N/A"),
                "fii_buy":  sf(latest.get("fiiBuy",0)),
                "fii_sell": sf(latest.get("fiiSell",0)),
                "fii_net":  sf(latest.get("fiiNet",0)),
                "dii_buy":  sf(latest.get("diiBuy",0)),
                "dii_sell": sf(latest.get("diiSell",0)),
                "dii_net":  sf(latest.get("diiNet",0)),
                "source":   "NSE official",
            }
    except: pass
    return {"date":"N/A","fii_buy":0,"fii_sell":0,"fii_net":0,
            "dii_buy":0,"dii_sell":0,"dii_net":0,"source":"unavailable"}

@st.cache_data(ttl=900)
def fetch_pcr():
    """Fetch NIFTY Put-Call Ratio from NSE."""
    try:
        s=requests.Session(); s.headers.update(REQUEST_HEADERS)
        s.get(NSE_HOME_URL,timeout=15)
        url="https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        r=s.get(url,headers={**REQUEST_HEADERS,"Referer":NSE_HOME_URL},timeout=15)
        r.raise_for_status(); data=r.json()
        filtered=data.get("filtered",{})
        ce_oi=sf(filtered.get("CE",{}).get("totOI",0))
        pe_oi=sf(filtered.get("PE",{}).get("totOI",0))
        pcr=round(pe_oi/ce_oi,2) if ce_oi>0 else np.nan
        return {"pcr":pcr,"ce_oi":ce_oi,"pe_oi":pe_oi,"source":"NSE official"}
    except: pass
    return {"pcr":np.nan,"ce_oi":0,"pe_oi":0,"source":"unavailable"}

@st.cache_data(ttl=900)
def fetch_news():
    rows=[]
    queries={"global_macro":'"Wall Street" OR "US markets" OR inflation OR tariffs OR oil OR crude OR bond yields',
             "india_market":'Nifty OR Sensex OR RBI OR rupee OR FII OR "Indian stock market"',
             "us_policy":'Trump OR "White House" OR tariffs OR oil OR Iran OR economy OR markets'}
    for bucket,q in queries.items():
        try:
            params={"query":q,"mode":"ArtList","maxrecords":18,"format":"json","sort":"DateDesc"}
            r=requests.get(GDELT_API,params=params,headers=REQUEST_HEADERS,timeout=20); r.raise_for_status()
            for a in r.json().get("articles",[]):
                title=a.get("title","").strip(); link=a.get("url","").strip()
                if title and link:
                    rows.append({"bucket":bucket,"title":title,"link":link,
                                 "source":a.get("domain",""),"pub_date":a.get("seendate",""),
                                 "score":headline_score(title),
                                 "sector_tags":", ".join(sector_impact(title))})
        except: pass
    for url,src,bkt in [(PIB_RSS_URL,"PIB","govt_policy")]:
        try:
            r=requests.get(url,headers=REQUEST_HEADERS,timeout=15); r.raise_for_status()
            root=ET.fromstring(r.text)
            for item in root.findall(".//item")[:15]:
                title=item.findtext("title","").strip(); link=item.findtext("link","").strip()
                if title and link:
                    rows.append({"bucket":bkt,"title":title,"link":link,"source":src,
                                 "pub_date":item.findtext("pubDate",""),
                                 "score":headline_score(title),"sector_tags":", ".join(sector_impact(title))})
        except: pass
    try:
        r=requests.get(RBI_PRESS_URL,headers=REQUEST_HEADERS,timeout=15); r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser"); count=0
        for a in soup.find_all("a",href=True):
            t=a.get_text(" ",strip=True); h=a["href"]
            if t and len(t)>15:
                fu=h if h.startswith("http") else f"https://www.rbi.org.in/{h.lstrip('/')}"
                rows.append({"bucket":"rbi_policy","title":t,"link":fu,"source":"RBI",
                             "pub_date":"","score":headline_score(t),"sector_tags":", ".join(sector_impact(t))})
                count+=1
                if count>=12: break
    except: pass
    if not rows: return pd.DataFrame(columns=["bucket","title","link","source","pub_date","score","sector_tags"])
    df=pd.DataFrame(rows).drop_duplicates(subset=["title","link"])
    df["pub_date"]=df["pub_date"].fillna("")
    return df.sort_values("pub_date",ascending=False)

def headline_score(text):
    t=text.lower(); s=0
    for w in POSITIVE_WORDS:
        if w in t: s+=1
    for w in NEGATIVE_WORDS:
        if w in t: s-=1
    if ("oil" in t or "crude" in t):
        if any(w in t for w in ["spike","surge","jumps"]): s-=2
        if any(w in t for w in ["falls","drops","eases"]): s+=1
    if "ceasefire" in t: s+=2
    if "tariff" in t: s-=2
    if "inflation" in t and any(w in t for w in ["hot","surge","spike"]): s-=2
    return s

def sector_impact(text):
    t=text.lower()
    return [sec for sec,kws in SECTOR_KEYWORDS.items() if any(k in t for k in kws)]

def news_bias(news_df):
    if news_df.empty: return {"score":0,"label":"NEUTRAL","reason":"No news.","top_positive":[],"top_negative":[]}
    total=int(news_df["score"].sum())
    label="POSITIVE" if total>=8 else ("NEGATIVE" if total<=-8 else "MIXED")
    reasons=[]
    if any(news_df["bucket"].eq("rbi_policy")): reasons.append("RBI active")
    if any(news_df["title"].str.contains("oil|crude",case=False,na=False)): reasons.append("oil-sensitive")
    if any(news_df["title"].str.contains("Trump|tariff",case=False,na=False)): reasons.append("US-policy risk")
    return {"score":total,"label":label,"reason":"; ".join(reasons) or "Mixed flow",
            "top_positive":news_df.sort_values("score",ascending=False).head(6)["title"].tolist(),
            "top_negative":news_df.sort_values("score").head(6)["title"].tolist()}

def overnight_score():
    snaps={k:get_quote(v) for k,v in GLOBAL_TICKERS.items()}
    score=0; reasons=[]
    us=np.nanmean([snaps[k].get("chg_pct",np.nan) for k in ["S&P 500","NASDAQ","DOW"]])
    asia=np.nanmean([snaps[k].get("chg_pct",np.nan) for k in ["NIKKEI","HANG SENG","SHANGHAI"]])
    brent=snaps["BRENT"].get("chg_pct",np.nan)
    if not np.isnan(us):
        if us>0.5: score+=2; reasons.append(f"Wall St +{us:.2f}%")
        elif us<-0.5: score-=2; reasons.append(f"Wall St {us:.2f}%")
    if not np.isnan(asia):
        if asia>0.4: score+=2; reasons.append(f"Asia +{asia:.2f}%")
        elif asia<-0.4: score-=2; reasons.append(f"Asia {asia:.2f}%")
    if not np.isnan(brent):
        if brent>1.5: score-=2; reasons.append(f"Brent +{brent:.2f}%")
        elif brent<-1.0: score+=1; reasons.append(f"Brent {brent:.2f}%")
    label="BULLISH OPEN" if score>=3 else ("WEAK OPEN" if score<=-3 else "MIXED OPEN")
    return {"label":label,"score":score,"reasons":reasons,"us_avg":us,"asia_avg":asia,
            "brent_chg":brent,"snaps":snaps}

def session_status(holidays):
    now=datetime.now(IST); today=now.date(); t=now.time()
    if today in holidays: return "Holiday"
    if now.weekday()==5: return "Saturday"
    if now.weekday()==6: return "Sunday"
    if t<time(9,0): return "Pre-Market"
    if time(9,0)<=t<time(9,15): return "Pre-Open"
    if time(9,15)<=t<=time(15,30): return "Live"
    if time(15,30)<t<=time(16,0): return "Post-Market"
    return "After Hours"

# ============================================================
# SCORING ENGINE
# ============================================================
def score_regime(nifty_df, nb, ov, breadth, vix_df):
    x=enrich(nifty_df)
    if x.empty: return {"label":"NEUTRAL","score":50,"reason":"Not enough data"}
    score=50; reasons=[]
    last=x.iloc[-1]
    if last["Close"]>last["EMA20"]:  score+=8;  reasons.append("↑EMA20")
    else: score-=8
    if last["EMA20"]>last["EMA50"]: score+=10; reasons.append("EMA stack")
    else: score-=10
    if last["Close"]>last["EMA200"]: score+=6; reasons.append("↑EMA200")
    else: score-=6
    r14=sf(last["RSI14"])
    if r14>57: score+=7; reasons.append(f"RSI {r14:.0f}")
    elif r14<43: score-=7
    if sf(last["MACD_HIST"])>0: score+=7; reasons.append("MACD+")
    else: score-=7
    slope=sf(last.get("EMA20_SLOPE",0))
    if slope>0.1: score+=5; reasons.append("trend acc.")
    elif slope<-0.1: score-=5
    bp=sf(breadth.get("adv_pct"),50)
    if bp>=65: score+=10; reasons.append(f"breadth {bp:.0f}%")
    elif bp>=55: score+=5
    elif bp<=40: score-=10
    if not vix_df.empty:
        try:
            vix=sf(vix_df["Close"].iloc[-1])
            if vix>22: score-=8; reasons.append(f"VIX {vix:.1f}")
            elif vix<14: score+=4; reasons.append(f"VIX low {vix:.1f}")
        except: pass
    if len(x)>=5:
        if x["OBV"].iloc[-1]>x["OBV"].iloc[-5]: score+=3; reasons.append("OBV↑")
        else: score-=2
    score+=max(-10,min(10,ov["score"]*2))
    score+=max(-6,min(6,nb["score"]))
    score=max(0,min(100,score))
    label="BULLISH" if score>=68 else ("BEARISH" if score<=36 else "NEUTRAL")
    return {"label":label,"score":round(score,2),"reason":", ".join(reasons[:6])+f" | {ov['label']} | News:{nb['label']}"}

def day_verdict(regime, ov, nb, vix_df, fii_data, pcr_data):
    score=(regime["score"]-50)/4.5+ov["score"]+max(-3,min(3,nb["score"]/3))
    if not vix_df.empty:
        try:
            vix=sf(vix_df["Close"].iloc[-1])
            if vix>22: score-=3
            elif vix<14: score+=1
        except: pass
    fii_net=sf(fii_data.get("fii_net",0))
    if fii_net>1000: score+=1.5
    elif fii_net<-1000: score-=1.5
    pcr=sf(pcr_data.get("pcr",np.nan))
    if not np.isnan(pcr):
        if pcr>1.2: score+=1
        elif pcr<0.7: score-=1
    if score>=6: return {"verdict":"TRADABLE","message":"Conditions supportive — size up on conviction setups.","score":round(score,2)}
    elif score<=-6: return {"verdict":"AVOID","message":"Unstable — protect capital, trade very selectively.","score":round(score,2)}
    return {"verdict":"SELECTIVE","message":"Mixed — only A-grade setups, strict stops.","score":round(score,2)}

def score_fundamentals(fund):
    score=50; notes=[]
    rg=sf(fund.get("revenue_growth")); eg=sf(fund.get("earnings_growth"))
    roe=sf(fund.get("roe")); pm=sf(fund.get("profit_margin"))
    de=sf(fund.get("debt_to_equity")); cr=sf(fund.get("current_ratio"))
    pe=sf(fund.get("trailing_pe")); pb=sf(fund.get("price_to_book"))
    peg=sf(fund.get("peg_ratio")); fs=sf(fund.get("f_score",0))
    if not np.isnan(rg):
        if rg>0.15: score+=12; notes.append(f"rev+{rg*100:.0f}%")
        elif rg>0.05: score+=5
        elif rg<0: score-=10; notes.append("rev↓")
    if not np.isnan(eg):
        if eg>0.15: score+=14; notes.append(f"EPS+{eg*100:.0f}%")
        elif eg>0.05: score+=6
        elif eg<-0.10: score-=14; notes.append("EPS↓")
    if not np.isnan(roe):
        if roe>0.20: score+=10; notes.append(f"ROE {roe*100:.0f}%")
        elif roe>0.12: score+=4
        elif roe<0.07: score-=6
    if not np.isnan(pm):
        if pm>0.15: score+=7; notes.append(f"margin {pm*100:.0f}%")
        elif pm>0.07: score+=3
        elif pm<0.03: score-=6
    if not np.isnan(de):
        if de<0.5: score+=9; notes.append("low debt")
        elif de<1.0: score+=4
        elif de>2.0: score-=12; notes.append("high debt")
    if not np.isnan(cr) and cr>=1.5: score+=4
    if not np.isnan(pe):
        if 0<pe<20: score+=5
        elif pe>80: score-=8; notes.append("rich PE")
    if not np.isnan(peg) and 0<peg<1.5: score+=5; notes.append(f"PEG {peg:.1f}")
    elif not np.isnan(peg) and peg>3: score-=5
    if fs>=7: score+=10; notes.append(f"F-Score {fs}/9")
    elif fs>=5: score+=4
    elif fs<=3: score-=8; notes.append(f"F-Score {fs}/9")
    score=max(0,min(100,score))
    block=(not np.isnan(eg) and eg<-0.25) and (not np.isnan(de) and de>2.0)
    return {"fund_score":score,"fund_notes":", ".join(notes[:5]) or "mixed","block_long":block}

def earnings_risk(fund):
    dt=fund.get("next_earnings_date")
    if dt is None or dt is pd.NaT: return {"earnings_penalty":0,"earnings_note":"no near earnings"}
    try:
        ed=pd.to_datetime(dt).to_pydatetime().replace(tzinfo=None)
        days=(ed.date()-datetime.now(IST).replace(tzinfo=None).date()).days
        if 0<=days<=3: return {"earnings_penalty":18,"earnings_note":f"earnings in {days}d ⚠️"}
        if 4<=days<=7: return {"earnings_penalty":10,"earnings_note":f"earnings in {days}d"}
        if days<0: return {"earnings_penalty":0,"earnings_note":"post-earnings"}
        return {"earnings_penalty":0,"earnings_note":f"earnings in {days}d"}
    except: return {"earnings_penalty":0,"earnings_note":"no near earnings"}

def sr_score(d):
    close_=sf(d.get("Close")); hh20=sf(d.get("HH20")); ll20=sf(d.get("LL20"))
    hh50=sf(d.get("HH50")); atr_=sf(d.get("ATR14")); donch=sf(d.get("DONCH20"))
    w52=sf(d.get("52W_PCT"))
    if any(pd.isna(v) for v in [close_,hh20,ll20,hh50]) or close_<=0: return 50,"mixed S/R"
    score=50; note="mixed S/R"
    dist_res=(hh50-close_)/close_; dist_sup=(close_-ll20)/close_
    if dist_res<0.015: score-=12; note="at resistance"
    elif dist_res<0.03: score-=6; note="near resistance"
    elif dist_sup<0.025 and close_>hh20*0.96: score+=10; note="healthy support"
    elif dist_res>0.06: score+=6; note="room to resistance"
    if not pd.isna(donch):
        if donch>=85: score+=5; note+=", near 52W high"
        elif donch<=20: score-=5; note+=", near 52W low"
    if not pd.isna(w52) and w52>=90: score+=5; note+=", near ATH"
    if not pd.isna(atr_) and atr_>0 and atr_/close_>0.05: score-=4; note+=", high ATR"
    return max(0,min(100,score)), note

def sector_strength_df(rank_df):
    if rank_df.empty or "sector" not in rank_df.columns: return pd.DataFrame()
    g=rank_df.groupby("sector").agg(
        avg_score=("base_score","mean"),avg_tech=("tech_score","mean"),
        avg_fund=("fund_score","mean"),avg_rs=("rs_score","mean"),
        avg_recent_perf=("recent_perf_score","mean"),
        buy_count=("signal",lambda s:(s=="BUY NOW").sum()),
        watch_count=("signal",lambda s:(s=="WATCH").sum()),
        stocks=("symbol","count"),
    ).reset_index()
    g["sector_score"]=(0.30*g["avg_score"]+0.20*g["avg_tech"]+0.15*g["avg_fund"]+
                       0.15*g["avg_rs"]+0.10*g["avg_recent_perf"]+
                       0.10*(g["buy_count"]/g["stocks"]*100)).round(2)
    return g.sort_values(["sector_score","buy_count"],ascending=[False,False]).reset_index(drop=True)

def score_stock(symbol, info, regime, nb, nifty_enr, sector_rank,
                prefetched_hist=None, prefetched_fund=None):
    name=info["name"]; sector=info["sector"]
    daily_raw = prefetched_hist if prefetched_hist is not None else fetch_hist(info["yf"],"1y")
    daily=enrich(daily_raw)
    empty_result={"symbol":symbol,"name":name,"sector":sector,"signal":"NO DATA","score":0,
                  "base_score":0,"tech_score":0,"rs_score":50,"news_score":50,"sector_score":50,
                  "fund_score":50,"recent_perf_score":50,"sr_score_val":50,"ltp":0,
                  "target1":0,"target2":0,"profit_pct_1":0,"profit_pct_2":0,"sl":0,
                  "stoploss_pct":0,"rr":0,"horizon":"N/A","why_selected":"No data",
                  "momentum_raw":0,"momentum_rank":0,"vol_ratio":0,"rsi":0,"donchian":0,
                  "obv_positive":False,"earning_note":"","setup_type":"N/A","confidence":"LOW",
                  "f_score":0,"52w_pct":0,"bb_squeeze":False}
    if daily.empty or nifty_enr.empty: return empty_result

    d=daily.iloc[-1]; n=nifty_enr.iloc[-1]
    close_=sf(d["Close"]); atr_=sf(d["ATR14"])

    # ── TECHNICAL ──────────────────────────────────────────
    tech=0; tech_notes=[]
    if close_>sf(d["EMA20"]):  tech+=12; tech_notes.append("↑EMA20")
    if close_>sf(d["EMA50"]):  tech+=10; tech_notes.append("↑EMA50")
    if sf(d["EMA20"])>sf(d["EMA50"]): tech+=8; tech_notes.append("stack")
    if close_>sf(d["EMA200"]): tech+=5;  tech_notes.append("↑EMA200")
    if sf(d["EMA9"])>sf(d["EMA20"]):  tech+=4;  tech_notes.append("EMA9↑")
    rsi_=sf(d["RSI14"])
    if 55<=rsi_<=72:  tech+=10; tech_notes.append(f"RSI {rsi_:.0f}")
    elif rsi_>72:     tech+=5;  tech_notes.append(f"RSI ob {rsi_:.0f}")
    elif rsi_<45:     tech-=8
    sr=sf(d["StochRSI"])
    if 20<=sr<=50:    tech+=5; tech_notes.append("StochRSI reset")
    elif sr>80:       tech-=4
    if sf(d["MACD_HIST"])>0: tech+=8; tech_notes.append("MACD+")
    vr=sf(d["VOL_RATIO"],1.0)
    if vr>=1.5:  tech+=10; tech_notes.append(f"vol {vr:.1f}x")
    elif vr>=1.15: tech+=5; tech_notes.append("vol↑")
    elif vr<0.7: tech-=5
    if sf(d["OBV"])>sf(d["OBV_EMA"]): tech+=5; tech_notes.append("OBV+")
    else: tech-=3
    donch=sf(d["DONCH20"])
    if donch>=90: tech+=8; tech_notes.append("52W zone")
    elif donch>=75: tech+=4
    elif donch<30: tech-=5
    # BB squeeze — compression before move
    bbs=sf(d["BB_SQUEEZE"]); bbsa=sf(d["BB_SQUEEZE_AVG"])
    bb_squeeze=False
    if not np.isnan(bbs) and not np.isnan(bbsa) and bbs<bbsa*0.85:
        bb_squeeze=True; tech+=7; tech_notes.append("BB squeeze🔥")
    # 52-week proximity bonus
    w52=sf(d.get("52W_PCT",50))
    if w52>=92: tech+=6; tech_notes.append("near 52W high")
    elif w52>=80: tech+=3
    # Gap detection (1D return > 1.5% with volume)
    ret1=sf(d.get("RET_1D",0))*100
    if ret1>1.5 and vr>=1.3: tech+=5; tech_notes.append("gap↑ vol")
    tech=max(0,min(100,tech))

    # ── RELATIVE STRENGTH ──────────────────────────────────
    rs=50; rs_notes=[]
    def rs_comp(sr,nr,w):
        nonlocal rs
        if pd.isna(sr) or pd.isna(nr): return
        diff=(sr-nr)*100
        if diff>5: rs+=w; rs_notes.append(f"RS+{w}")
        elif diff>2: rs+=w//2
        elif diff<-5: rs-=w
        elif diff<-2: rs-=w//2
    rs_comp(sf(d["RET_5D"]),sf(n["RET_5D"]),8)
    rs_comp(sf(d["RET_20D"]),sf(n["RET_20D"]),12)
    rs_comp(sf(d["RET_60D"]),sf(n["RET_60D"]),8)
    # RS acceleration
    rs5=(sf(d.get("RET_5D",0))-sf(n.get("RET_5D",0)))*100
    rs10=(sf(d.get("RET_10D",0))-sf(n.get("RET_10D",0)))*100
    if not pd.isna(rs5) and not pd.isna(rs10) and rs5>rs10:
        rs+=6; rs_notes.append("RS accel")
    rs=max(0,min(100,rs))

    # ── NEWS ───────────────────────────────────────────────
    from_news=50; comp_hits=0; sec_hits=0
    for h in nb.get("top_positive",[])+nb.get("top_negative",[]):
        t=h.lower()
        if symbol.lower() in t or name.lower() in t: comp_hits+=2
        if sector.lower() in t: sec_hits+=1
        for kw in SECTOR_KEYWORDS.get(sector,[]): 
            if kw in t: sec_hits+=0.5
    from_news+=min(comp_hits*5+sec_hits*2,25)
    if regime["label"]=="BULLISH": from_news+=4
    elif regime["label"]=="BEARISH": from_news-=8
    from_news=max(0,min(100,from_news))

    # ── FUNDAMENTAL ────────────────────────────────────────
    fund = prefetched_fund if prefetched_fund is not None else fetch_fundamentals(symbol, info["yf"])
    fe=score_fundamentals(fund)
    rp=sf(fund.get("recent_perf_score",50)); rp_n=fund.get("recent_perf_notes","")
    ee=earnings_risk(fund)
    srs,sr_note=sr_score(d)
    sec_sc=sf((sector_rank or {}).get(sector,50))
    sec_note=("leading" if sec_sc>=72 else ("lagging" if sec_sc<=42 else "average"))+" sector"
    fs_val=int(sf(fund.get("f_score",0)))

    # ── COMPOSITE ──────────────────────────────────────────
    base=(0.28*tech+0.20*rp+0.15*rs+0.14*sec_sc+0.09*from_news+0.08*regime["score"]+0.06*srs)
    penalty=ee["earnings_penalty"]
    if fe["block_long"]: penalty+=12
    if regime["label"]=="BEARISH": penalty+=15
    final=round(max(0,min(100,base-penalty)),2)

    setup=classify_setup(d)
    conf="HIGH" if final>=72 else ("MEDIUM" if final>=58 else "LOW")
    if fe["block_long"] or regime["label"]=="BEARISH": signal="AVOID"
    elif final>=72: signal="BUY NOW"
    elif final>=60: signal="WATCH"
    elif final>=49: signal="AGGRESSIVE"
    else: signal="AVOID"

    # ── TARGETS ────────────────────────────────────────────
    if pd.isna(atr_) or atr_<=0: sl=round(close_*0.95,2)
    else:
        mult={"BB Squeeze Breakout":1.0,"Volume Breakout":1.1,"Breakout":1.3,
              "Momentum Surge":1.0,"EMA Pullback":1.6,"Oversold Bounce":1.8,
              "StochRSI Reset":1.5,"Trend":1.4}.get(setup,1.4)
        sl=round(close_-mult*atr_,2)
    risk=max(close_-sl,0.01)
    t1=round(close_+2.0*risk,2); t2=round(close_+3.5*risk,2)
    pp1=round(((t1/close_)-1)*100,2); pp2=round(((t2/close_)-1)*100,2)
    sl_pct=round((1-sl/close_)*100,2); rr=round((t1-close_)/risk,2)
    horizon=("Avoid pre-results" if ee["earnings_penalty"]>=12 else ("2–4 weeks" if pp2>=10 else "1–2 weeks"))
    ret_mom=(sf(d.get("RET_1D",0))*100*0.2+sf(d.get("RET_5D",0))*100*0.4+sf(d.get("RET_20D",0))*100*0.4)
    why=" | ".join(filter(None,[" ".join(tech_notes[:3])," ".join(rs_notes[:1]),
                                sec_note if "average" not in sec_note else "",
                                rp_n[:50] if rp_n else "",sr_note,ee["earnings_note"]]))[:200]
    return {
        "symbol":symbol,"name":name,"sector":sector,
        "signal":signal,"confidence":conf,"setup_type":setup,
        "score":final,"base_score":round(base,2),
        "tech_score":round(tech,2),"rs_score":round(rs,2),
        "news_score":round(from_news,2),"sector_score":round(sec_sc,2),
        "fund_score":round(fe["fund_score"],2),"recent_perf_score":round(rp,2),
        "sr_score_val":round(srs,2),"f_score":fs_val,
        "ltp":round(close_,2),"target1":t1,"target2":t2,
        "profit_pct_1":pp1,"profit_pct_2":pp2,"sl":sl,"stoploss_pct":sl_pct,
        "rr":rr,"horizon":horizon,"why_selected":why,
        "momentum_raw":round(ret_mom,2),"momentum_rank":0,
        "vol_ratio":round(vr,2),"rsi":round(rsi_,1),"donchian":round(donch,1),
        "obv_positive":sf(d["OBV"])>sf(d["OBV_EMA"]),"earning_note":ee["earnings_note"],
        "bb_squeeze":bb_squeeze,"52w_pct":round(w52,1),
    }

# ============================================================
# PLOTLY CHART BUILDERS
# ============================================================
PLOT_THEME = dict(
    paper_bgcolor="#10131c", plot_bgcolor="#10131c",
    font=dict(color="#7a84a0", family="Space Mono, monospace", size=10),
    xaxis=dict(gridcolor="rgba(255,255,255,0.04)", showgrid=True, zeroline=False, color="#7a84a0"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showgrid=True, zeroline=False, color="#7a84a0"),
)

def candlestick_chart(df, symbol, name, enriched=None):
    if df.empty: return None
    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[0.6,0.2,0.2],
                      vertical_spacing=0.03,
                      subplot_titles=[f"{symbol} — {name}","Volume","RSI 14"])
    # candles
    fig.add_trace(go.Candlestick(x=df.index,open=df["Open"],high=df["High"],
                                  low=df["Low"],close=df["Close"],name="Price",
                                  increasing_line_color="#00ffa3",decreasing_line_color="#ff4757",
                                  increasing_fillcolor="rgba(0,255,163,0.6)",
                                  decreasing_fillcolor="rgba(255,71,87,0.6)"),row=1,col=1)
    if enriched is not None and not enriched.empty:
        for ema,col in [("EMA20","#4ea8ff"),("EMA50","#ffd166"),("EMA200","#a78bfa")]:
            if ema in enriched.columns:
                fig.add_trace(go.Scatter(x=enriched.index,y=enriched[ema],name=ema,
                                          line=dict(color=col,width=1.2),opacity=0.85),row=1,col=1)
        # BB bands
        if "BB_UPPER" in enriched.columns:
            fig.add_trace(go.Scatter(x=enriched.index,y=enriched["BB_UPPER"],name="BB Upper",
                                      line=dict(color="rgba(167,139,250,0.4)",width=1,dash="dot")),row=1,col=1)
            fig.add_trace(go.Scatter(x=enriched.index,y=enriched["BB_LOWER"],name="BB Lower",
                                      line=dict(color="rgba(167,139,250,0.4)",width=1,dash="dot"),
                                      fill="tonexty",fillcolor="rgba(167,139,250,0.03)"),row=1,col=1)
        # volume
        vol_colors=["#00ffa3" if c>=o else "#ff4757" for c,o in zip(df["Close"],df["Open"])]
        fig.add_trace(go.Bar(x=df.index,y=df["Volume"],name="Volume",
                              marker_color=vol_colors,opacity=0.7),row=2,col=1)
        if "VOL20" in enriched.columns:
            fig.add_trace(go.Scatter(x=enriched.index,y=enriched["VOL20"],name="Vol MA20",
                                      line=dict(color="#ffd166",width=1)),row=2,col=1)
        # RSI
        if "RSI14" in enriched.columns:
            fig.add_trace(go.Scatter(x=enriched.index,y=enriched["RSI14"],name="RSI14",
                                      line=dict(color="#00e5ff",width=1.5)),row=3,col=1)
            fig.add_hline(y=70,line_dash="dot",line_color="rgba(255,71,87,0.4)",row=3,col=1)
            fig.add_hline(y=30,line_dash="dot",line_color="rgba(0,255,163,0.4)",row=3,col=1)
            fig.add_hline(y=50,line_dash="dot",line_color="rgba(255,255,255,0.1)",row=3,col=1)
    fig.update_layout(**PLOT_THEME,height=580,showlegend=False,
                      margin=dict(l=10,r=10,t=30,b=10),
                      xaxis_rangeslider_visible=False)
    return fig

def nifty_regime_chart(nifty_enr, regime):
    if nifty_enr.empty: return None
    df=nifty_enr.tail(120)
    color="#00ffa3" if regime["label"]=="BULLISH" else ("#ff4757" if regime["label"]=="BEARISH" else "#ffd166")
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=df.index,y=df["Close"],name="NIFTY",
                              line=dict(color=color,width=2),fill="tozeroy",
                              fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.06)"))
    for ema,c in [("EMA20","#4ea8ff"),("EMA50","#ffd166")]:
        fig.add_trace(go.Scatter(x=df.index,y=df[ema],name=ema,
                                  line=dict(color=c,width=1.2,dash="dot")))
    fig.update_layout(**PLOT_THEME,height=260,showlegend=True,
                      margin=dict(l=10,r=10,t=20,b=10),
                      legend=dict(orientation="h",y=1.1,font=dict(size=9)))
    return fig

def returns_heatmap(rank_df):
    if rank_df.empty: return None
    df=rank_df[["symbol","sector","ltp"]].copy()
    df["1D%"]  =rank_df.get("rsi",pd.Series()).values  # proxy — use actual ret if available
    cols=["symbol","sector","score","tech_score","rs_score","fund_score","vol_ratio","rsi","donchian"]
    available=[c for c in cols if c in rank_df.columns]
    hdf=rank_df[available].set_index("symbol")
    # build a simple heatmap of score components
    plot_cols=["score","tech_score","rs_score","fund_score"]
    plot_cols=[c for c in plot_cols if c in hdf.columns]
    if not plot_cols: return None
    z=hdf[plot_cols].values.T
    fig=go.Figure(go.Heatmap(z=z,x=hdf.index.tolist(),y=plot_cols,
                              colorscale=[[0,"#ff4757"],[0.5,"#1a1f33"],[1,"#00ffa3"]],
                              zmid=50,text=np.round(z,0).astype(int),texttemplate="%{text}",
                              showscale=True,colorbar=dict(thickness=10,tickfont=dict(size=9))))
    fig.update_layout(**PLOT_THEME,height=220,margin=dict(l=80,r=10,t=20,b=60),
                      xaxis=dict(tickangle=-45,tickfont=dict(size=8)),
                      yaxis=dict(tickfont=dict(size=9)))
    return fig

def sector_radar(sector_df):
    if sector_df.empty or len(sector_df)<3: return None
    cats=sector_df["sector"].tolist(); vals=sector_df["sector_score"].tolist()
    cats.append(cats[0]); vals.append(vals[0])
    fig=go.Figure(go.Scatterpolar(r=vals,theta=cats,fill="toself",
                                   fillcolor="rgba(0,255,163,0.07)",
                                   line=dict(color="#00ffa3",width=1.5),
                                   marker=dict(color="#00ffa3",size=5)))
    fig.update_layout(paper_bgcolor="#10131c",plot_bgcolor="#10131c",
                      polar=dict(bgcolor="#10131c",
                                 radialaxis=dict(visible=True,range=[0,100],gridcolor="rgba(255,255,255,0.05)",tickfont=dict(size=8,color="#7a84a0")),
                                 angularaxis=dict(gridcolor="rgba(255,255,255,0.06)",tickfont=dict(size=9,color="#e4e8f5"))),
                      showlegend=False,height=380,margin=dict(l=30,r=30,t=20,b=20))
    return fig

def breadth_bar(breadth):
    if not breadth: return None
    adv=sf(breadth.get("advances",0)); dec=sf(breadth.get("declines",0)); unch=sf(breadth.get("unchanged",0))
    if adv+dec+unch==0: return None
    fig=go.Figure(go.Bar(x=["Advances","Declines","Unchanged"],y=[adv,dec,unch],
                          marker_color=["#00ffa3","#ff4757","#7a84a0"],
                          text=[int(adv),int(dec),int(unch)],textposition="outside",
                          textfont=dict(color=["#00ffa3","#ff4757","#7a84a0"],size=10)))
    fig.update_layout(**PLOT_THEME,height=200,showlegend=False,
                      margin=dict(l=10,r=10,t=15,b=10),
                      yaxis=dict(showgrid=False,showticklabels=False))
    return fig

def score_history_chart(hist_df):
    if hist_df.empty: return None
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=hist_df["date"],y=hist_df["score"],name="Score",
                              line=dict(color="#00ffa3",width=2),mode="lines+markers",
                              marker=dict(size=5)))
    fig.add_hline(y=72,line_dash="dot",line_color="rgba(0,255,163,0.4)")
    fig.add_hline(y=50,line_dash="dot",line_color="rgba(255,255,255,0.1)")
    fig.update_layout(**PLOT_THEME,height=180,showlegend=False,
                      margin=dict(l=10,r=10,t=15,b=10))
    return fig

# ============================================================
# UI HELPERS
# ============================================================
def pill(label,kind="blue"):
    return f'<span class="pill pill-{kind}">{label}</span>'

def regime_pill(label):
    m={"BULLISH":"green","BEARISH":"red","NEUTRAL":"amber","TRADABLE":"green","AVOID":"red",
       "SELECTIVE":"amber","BULLISH OPEN":"green","WEAK OPEN":"red","MIXED OPEN":"amber",
       "POSITIVE":"green","NEGATIVE":"red","MIXED":"amber"}
    return pill(label, m.get(label,"blue"))

def bar_html(pct,color="green"):
    v=max(0,min(100,sf(pct,0)))
    return f'<div class="bar"><div class="bar-fill {color}" style="width:{v:.0f}%"></div></div>'

def score_ring(score,size=46):
    pct=max(0,min(100,sf(score,0)))
    color="var(--green)" if pct>=65 else ("var(--amber)" if pct>=48 else "var(--red)")
    conic=f"conic-gradient({color} {pct*3.6:.0f}deg,rgba(255,255,255,0.07) 0)"
    return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{conic};'
            f'display:flex;align-items:center;justify-content:center;position:relative;">'
            f'<div style="position:absolute;inset:5px;background:var(--panel);border-radius:50%;"></div>'
            f'<span style="position:relative;z-index:1;font-family:\'Space Mono\',monospace;'
            f'font-size:.7rem;font-weight:700;color:white;">{pct:.0f}</span></div>')

def fscore_badge(val):
    cls="fscore-hi" if val>=7 else ("fscore-md" if val>=5 else "fscore-lo")
    return f'<span class="fscore-badge {cls}">{val}</span>'

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:900;
    background:linear-gradient(110deg,#00ffa3,#00e5ff);-webkit-background-clip:text;
    -webkit-text-fill-color:transparent;margin-bottom:.5rem;">⚡ MARKETSENSE PRO</div>
    <div style="font-size:.72rem;color:#7a84a0;margin-bottom:1rem;">v6 · India Equities</div>""",
    unsafe_allow_html=True)
    st.markdown("---")
    max_ideas  = st.slider("Top ideas",5,20,10,1)
    min_fund   = st.slider("Min fundamental score",20,80,40,5)
    max_sl     = st.slider("Max stoploss %",5,15,10,1)
    min_rr     = st.slider("Min risk:reward",1.0,3.0,1.3,.1)
    capital    = st.number_input("Capital (₹)",min_value=10_000,value=100_000,step=10_000)
    risk_pct   = st.slider("Risk per trade (%)",0.25,2.0,1.0,.25)
    st.markdown("---")
    st.markdown("**Alerts — Quick Filters**")
    alert_rsi_min = st.slider("RSI ≥",30,80,55,5)
    alert_vol_min = st.slider("Vol ratio ≥",1.0,3.0,1.2,.1)
    alert_score_min=st.slider("Score ≥",40,90,60,5)
    st.markdown("---")
    st.caption("Auto-refresh: 15 min · Yahoo Finance · GDELT · NSE · RBI")

# ============================================================
# LOAD DATA
# ============================================================
holiday_df  = fetch_holidays()
holiday_set = set(holiday_df["date"].tolist()) if not holiday_df.empty else set()
now_ist     = datetime.now(IST)
sess_st     = session_status(holiday_set)

with st.spinner("⚡ Loading market intelligence (parallel fetch)..."):
    news_df_raw = fetch_news()
    nb          = news_bias(news_df_raw)
    ov          = overnight_score()
    official_b  = fetch_breadth()
    fii_data    = fetch_fii_dii()
    pcr_data    = fetch_pcr()
    nifty_raw   = fetch_hist("^NSEI","1y")
    nifty_enr   = enrich(nifty_raw)
    vix_raw     = fetch_hist("^INDIAVIX","1y")
    regime      = score_regime(nifty_raw,nb,ov,official_b,vix_raw)
    dv          = day_verdict(regime,ov,nb,vix_raw,fii_data,pcr_data)

with st.spinner("⚡ Parallel-fetching all stock data..."):
    all_hist = parallel_fetch_universe(SCAN_UNIVERSE)
    all_fund = parallel_fetch_fundamentals(SCAN_UNIVERSE)

breadth_data = official_b if official_b else {"adv_pct":50,"source":"estimate"}

# ── Phase 1 scan (no sector rank yet) ──
with st.spinner("🔍 Phase 1 scan..."):
    p1 = []
    for sym,info in SCAN_UNIVERSE.items():
        p1.append(score_stock(sym,info,regime,nb,nifty_enr,None,
                               all_hist.get(sym),all_fund.get(sym)))
    p1_df=pd.DataFrame(p1)
    sector_df_p1=sector_strength_df(p1_df)
    sec_map={r["sector"]:r["sector_score"] for _,r in sector_df_p1.iterrows()}

# ── Phase 2 scan (with sector rank) ──
with st.spinner("🎯 Phase 2 refinement..."):
    p2=[]
    for sym,info in SCAN_UNIVERSE.items():
        p2.append(score_stock(sym,info,regime,nb,nifty_enr,sec_map,
                               all_hist.get(sym),all_fund.get(sym)))
    rank_df=pd.DataFrame(p2)
    rank_df["momentum_rank"]=rank_df["momentum_raw"].rank(pct=True).mul(100).round(0).astype(int)
    rank_df=rank_df.sort_values(["score","profit_pct_2","tech_score"],ascending=False).reset_index(drop=True)
    sector_df=sector_strength_df(rank_df)
    save_scores(rank_df)   # persist daily history

# ── Filtered buckets ──
ideas=rank_df[(rank_df["signal"].isin(["BUY NOW","WATCH","AGGRESSIVE"]))&
              (rank_df["fund_score"]>=max(25,min_fund-15))&
              (rank_df["stoploss_pct"]<=max_sl+2)&
              (rank_df["rr"]>=max(1.1,min_rr-.3))].head(max_ideas)
if ideas.empty: ideas=rank_df[rank_df["signal"].isin(["BUY NOW","WATCH","AGGRESSIVE"])].head(max_ideas)
if regime["label"]=="BEARISH": ideas=ideas.head(0)

high_conv  = rank_df[(rank_df["signal"]=="BUY NOW")&(rank_df["confidence"]=="HIGH")&(rank_df["rr"]>=1.5)].head(6)
watch_list = rank_df[rank_df["signal"].isin(["BUY NOW","WATCH"])&(rank_df["fund_score"]>=30)].head(8)
aggressive = rank_df[rank_df["signal"].isin(["BUY NOW","WATCH","AGGRESSIVE"])&(rank_df["fund_score"]>=22)].head(10)

# ── Alert engine ──
alerts=rank_df[(rank_df["rsi"]>=alert_rsi_min)&
               (rank_df["vol_ratio"]>=alert_vol_min)&
               (rank_df["score"]>=alert_score_min)].sort_values("score",ascending=False)

# ============================================================
# HEADER BAR
# ============================================================
nifty_q   = get_quote("^NSEI")
nifty_chg = sf(nifty_q.get("chg_pct"),0)
nifty_last= sf(nifty_q.get("last"),0)
nifty_color="green" if nifty_chg>=0 else "red"
nifty_arrow="▲" if nifty_chg>=0 else "▼"
nifty_sub = "up" if nifty_chg>=0 else "dn"

vix_val   = sf(vix_raw["Close"].iloc[-1]) if not vix_raw.empty else np.nan
vix_str   = f"{vix_val:.1f}" if not np.isnan(vix_val) else "N/A"
vix_color = "green" if (not np.isnan(vix_val) and vix_val<16) else ("red" if (not np.isnan(vix_val) and vix_val>22) else "amber")
vix_lbl   = "calm" if (not np.isnan(vix_val) and vix_val<16) else ("elevated" if (not np.isnan(vix_val) and vix_val>22) else "moderate")

bp        = sf(breadth_data.get("adv_pct"),50)
bp_color  = "green" if bp>=55 else ("red" if bp<45 else "amber")
us_avg    = sf(ov.get("us_avg"),0)
us_arrow  = "▲" if us_avg>=0 else "▼"
us_color  = "green" if us_avg>=0 else "red"
brent_q   = ov.get("snaps",{}).get("BRENT",{})
brent_chg = sf(brent_q.get("chg_pct"),0)
brent_last= sf(brent_q.get("last"),0)
brent_color="red" if brent_chg>1 else ("green" if brent_chg<-1 else "amber")
brent_sub = "dn" if brent_chg>1 else ("up" if brent_chg<-1 else "")
reg_color = "green" if regime["label"]=="BULLISH" else ("red" if regime["label"]=="BEARISH" else "amber")
pcr_val   = sf(pcr_data.get("pcr"),np.nan)
pcr_str   = f"{pcr_val:.2f}" if not np.isnan(pcr_val) else "N/A"
pcr_color = "green" if (not np.isnan(pcr_val) and pcr_val>1.2) else ("red" if (not np.isnan(pcr_val) and pcr_val<0.7) else "amber")
fii_net   = sf(fii_data.get("fii_net"),0)
fii_color = "green" if fii_net>0 else "red"
fii_str   = f"₹{fii_net:+,.0f}Cr"

st.markdown(f"""
<div class="ms-topbar">
  <div class="ms-logo">MARKETSENSE<sup style="-webkit-text-fill-color:var(--muted);font-family:'Space Mono',monospace;font-size:.52rem;">PRO v6</sup></div>
  <div style="display:flex;gap:7px;flex-wrap:wrap;align-items:center;">
    {regime_pill(regime['label'])}
    {regime_pill(dv['verdict'])}
    {regime_pill(ov['label'])}
    {pill(sess_st,'blue')}
    {regime_pill(nb['label'])}
  </div>
  <div class="ms-meta">
    <b>{now_ist.strftime('%d %b %Y')}</b> · {now_ist.strftime('%H:%M IST')}<br>
    Score <b>{regime['score']}/100</b> · Breadth <b>{bp:.1f}%</b> · PCR <b>{pcr_str}</b>
  </div>
</div>
""", unsafe_allow_html=True)

# ── STAT STRIP ──
st.markdown(f"""
<div class="stat-strip">
  <div class="stat-cell {nifty_color}">
    <div class="stat-label">NIFTY 50</div>
    <div class="stat-val">{nifty_last:,.2f}</div>
    <div class="stat-sub {nifty_sub}">{nifty_arrow} {abs(nifty_chg):.2f}%</div>
  </div>
  <div class="stat-cell {vix_color}">
    <div class="stat-label">INDIA VIX</div>
    <div class="stat-val">{vix_str}</div>
    <div class="stat-sub">{vix_lbl}</div>
  </div>
  <div class="stat-cell {pcr_color}">
    <div class="stat-label">Put-Call Ratio</div>
    <div class="stat-val">{pcr_str}</div>
    <div class="stat-sub">{'bullish' if not np.isnan(pcr_val) and pcr_val>1.2 else ('bearish' if not np.isnan(pcr_val) and pcr_val<0.7 else 'neutral')}</div>
  </div>
  <div class="stat-cell {fii_color}">
    <div class="stat-label">FII Net Flow</div>
    <div class="stat-val" style="font-size:1.1rem;">{fii_str}</div>
    <div class="stat-sub">DII: ₹{sf(fii_data.get('dii_net'),0):+,.0f}Cr</div>
  </div>
  <div class="stat-cell {us_color}">
    <div class="stat-label">Wall Street</div>
    <div class="stat-val">{us_arrow} {abs(us_avg):.2f}%</div>
    <div class="stat-sub">SPX/NDX/DJI avg</div>
  </div>
  <div class="stat-cell {brent_color}">
    <div class="stat-label">Brent Crude</div>
    <div class="stat-val">${brent_last:.1f}</div>
    <div class="stat-sub {brent_sub}">{brent_chg:+.2f}%</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── CONTEXT PANELS ──
st.markdown(f"""
<div class="ctx-grid">
  <div class="ctx-card">
    <div class="ctx-title">Session Analysis</div>
    <div class="ctx-body">
      <b>Verdict:</b> {dv['verdict']} — {dv['message']}<br><br>
      <b>Overnight:</b> {ov['label']} — {' · '.join(ov['reasons'][:4]) or 'No major cues'}<br><br>
      <b>FII/DII:</b> FII {fii_str} · DII ₹{sf(fii_data.get('dii_net'),0):+,.0f}Cr ({fii_data.get('date','N/A')})<br>
      <b>PCR:</b> {pcr_str} · <b>VIX:</b> {vix_str}
    </div>
  </div>
  <div class="ctx-card">
    <div class="ctx-title">Regime & Intelligence</div>
    <div class="ctx-body">
      <b>Regime:</b> {regime['label']} ({regime['score']}/100)<br>
      {regime['reason'][:120]}<br><br>
      <b>News:</b> {nb['label']} (score {nb['score']}) — {nb['reason']}<br>
      <b>Breadth:</b> {bp:.1f}% advancing · {breadth_data.get('source','estimate')}
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# TABS
# ============================================================
tabs = st.tabs([
    "🏠 Dashboard","📈 Charts","📊 Indices & Global",
    "🎯 Ideas Grid","🏆 Sectors","⚡ Options",
    "🔔 Alerts","🔍 Deep Dive","📅 Calendar",
    "📋 Full Scan","📰 News",
])

# ─────────────────────────────────────────────────────────────
# TAB 0 — DASHBOARD
# ─────────────────────────────────────────────────────────────
with tabs[0]:
    if regime["label"]=="BEARISH":
        st.markdown('<div class="warn-strip">⚠️ BEARISH REGIME — idea generation paused. Protect capital.</div>',unsafe_allow_html=True)
    elif regime["label"]=="BULLISH":
        st.markdown('<div class="good-strip">✅ BULLISH REGIME — full scan active. Focus on volume + strong RS setups.</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="amber-strip">⚠️ NEUTRAL REGIME — trade only top-quality setups with tight stops.</div>',unsafe_allow_html=True)

    # Regime meter
    rc={"BULLISH":"var(--green)","BEARISH":"var(--red)","NEUTRAL":"var(--amber)"}
    st.markdown(f"""
    <div class="regime-meter">
      <div>
        <div style="font-family:'Space Mono',monospace;font-size:.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px;">Regime Confidence</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;color:{rc.get(regime['label'],'white')};">{regime['label']}</div>
      </div>
      <div class="regime-bar"><div class="regime-fill" style="width:{regime['score']}%"></div></div>
      <div class="regime-score">{regime['score']}/100</div>
    </div>""",unsafe_allow_html=True)

    # NIFTY mini chart
    nifty_chart=nifty_regime_chart(nifty_enr,regime)
    if nifty_chart: st.plotly_chart(nifty_chart,use_container_width=True,config={"displayModeBar":False})

    # Top idea cards
    st.markdown('<div class="sec-title">High-Conviction Ideas</div>',unsafe_allow_html=True)
    disp=high_conv if not high_conv.empty else ideas.head(4)
    if disp.empty:
        st.info("No high-conviction ideas under current regime.")
    else:
        cols=st.columns(min(4,len(disp)))
        for col,(_,row) in zip(cols,disp.iterrows()):
            sl=row["signal"]; s_lower="buy" if sl=="BUY NOW" else ("watch" if sl=="WATCH" else "skip")
            bc="green" if row["score"]>=65 else ("amber" if row["score"]>=50 else "red")
            with col:
                st.markdown(f"""
                <div class="idea-card {s_lower}">
                  <div class="card-ticker">{row['symbol']} · {row['sector']}</div>
                  <div class="card-name">{row['name']}</div>
                  <div class="card-signal {s_lower}">{row['signal']}</div>
                  <div class="card-badge">{row['setup_type']}</div>
                  <div style="display:flex;align-items:center;gap:10px;margin:6px 0;">
                    {score_ring(row['score'],42)}
                    <div>
                      <div style="font-size:.7rem;color:var(--muted);">F-Score</div>
                      {fscore_badge(row['f_score'])}
                    </div>
                  </div>
                  {bar_html(row['score'],bc)}
                  <div class="card-row"><span class="k">LTP</span><span class="v">₹{row['ltp']:,.2f}</span></div>
                  <div class="card-row"><span class="k">Target 1</span><span class="v up">₹{row['target1']:,.2f} +{row['profit_pct_1']}%</span></div>
                  <div class="card-row"><span class="k">Target 2</span><span class="v up">₹{row['target2']:,.2f} +{row['profit_pct_2']}%</span></div>
                  <div class="card-row"><span class="k">Stop Loss</span><span class="v dn">₹{row['sl']:,.2f} -{row['stoploss_pct']}%</span></div>
                  <div class="card-row"><span class="k">R:R / RSI</span><span class="v">{row['rr']} / {row['rsi']}</span></div>
                  <div class="card-row"><span class="k">52W%</span><span class="v">{'🔥' if row['52w_pct']>=90 else ''}{row['52w_pct']:.0f}%</span></div>
                  <div class="card-row"><span class="k">BB Squeeze</span><span class="v">{'🔥 YES' if row['bb_squeeze'] else 'No'}</span></div>
                  <div class="card-row"><span class="k">Horizon</span><span class="v">{row['horizon']}</span></div>
                  <div class="card-why">{row['why_selected']}</div>
                </div>""",unsafe_allow_html=True)

    # Signal buckets + position sizer
    st.markdown('<div class="sec-title">Signal Buckets</div>',unsafe_allow_html=True)
    bc1,bc2,bc3=st.columns(3)
    for col,title,dfb in [(bc1,"High Conviction",high_conv),(bc2,"Watch / Pullback",watch_list),(bc3,"Aggressive",aggressive)]:
        with col:
            st.markdown(f'<div class="ctx-card"><div class="ctx-title">{title}</div>',unsafe_allow_html=True)
            if dfb.empty: st.caption("No names currently")
            else:
                for _,r in dfb.head(5).iterrows():
                    sl2=r["signal"]; s2="green" if sl2=="BUY NOW" else ("amber" if sl2=="WATCH" else "red")
                    obvi="🟢" if r.get("obv_positive") else "🔴"
                    sq="🔥" if r.get("bb_squeeze") else ""
                    st.markdown(f"""
                    <div style="margin-bottom:9px;padding-bottom:9px;border-bottom:1px solid rgba(255,255,255,0.05);">
                      <div style="display:flex;justify-content:space-between;">
                        <b style="color:white;font-size:.88rem;">{r['symbol']}</b>
                        <span class="pill pill-{s2}" style="font-size:.6rem;">{sl2}</span>
                      </div>
                      <div style="font-size:.74rem;color:var(--muted);">{r['name']}</div>
                      <div style="font-size:.73rem;margin-top:4px;display:flex;gap:8px;">
                        <span>Score <b style="color:white;">{r['score']}</b></span>
                        <span style="color:var(--muted);">RSI {r['rsi']}</span>
                        <span>{obvi} OBV</span>
                        <span>{sq}</span>
                      </div>
                    </div>""",unsafe_allow_html=True)
            st.markdown('</div>',unsafe_allow_html=True)

    # Breadth chart + position sizer side by side
    st.markdown('<div class="sec-title">Market Breadth & Position Sizer</div>',unsafe_allow_html=True)
    pb_col, ps_col = st.columns([1, 1])
    with pb_col:
        bf=breadth_bar(official_b)
        if bf: st.plotly_chart(bf,use_container_width=True,config={"displayModeBar":False})
        else: st.caption("Breadth data unavailable")
    with ps_col:
        if not ideas.empty:
            best=ideas.iloc[0]
            risk_amt=capital*(risk_pct/100)
            per_share=max(best["ltp"]-best["sl"],0.01)
            qty=int(risk_amt//per_share)
            invest_val=round(qty*best["ltp"],2)
            st.markdown(f"""
            <div class="sizer-card">
              <div class="sizer-title">📐 {best['name']} ({best['symbol']})</div>
              <div class="sizer-row"><span class="sk">Capital</span><span class="sv">₹{capital:,.0f}</span></div>
              <div class="sizer-row"><span class="sk">Risk ({risk_pct}%)</span><span class="sv">₹{risk_amt:,.0f}</span></div>
              <div class="sizer-row"><span class="sk">Entry LTP</span><span class="sv">₹{best['ltp']:,.2f}</span></div>
              <div class="sizer-row"><span class="sk">Stop Loss</span><span class="sv">₹{best['sl']:,.2f} (-{best['stoploss_pct']}%)</span></div>
              <div class="sizer-row"><span class="sk">Risk/share</span><span class="sv">₹{per_share:,.2f}</span></div>
              <div class="sizer-row"><span class="sk">Qty</span><span class="sv big">{qty} shares</span></div>
              <div class="sizer-row"><span class="sk">Investment</span><span class="sv">₹{invest_val:,.0f} ({invest_val/capital*100:.1f}%)</span></div>
              <div class="sizer-row"><span class="sk">T1 P&L</span><span class="sv" style="color:var(--green);">+₹{qty*(best['target1']-best['ltp']):,.0f}</span></div>
              <div class="sizer-row"><span class="sk">T2 P&L</span><span class="sv" style="color:var(--green);">+₹{qty*(best['target2']-best['ltp']):,.0f}</span></div>
            </div>""",unsafe_allow_html=True)
        else:
            st.info("No eligible idea for sizing.")

# ─────────────────────────────────────────────────────────────
# TAB 1 — CHARTS
# ─────────────────────────────────────────────────────────────
with tabs[1]:
    st.markdown('<div class="sec-title">Interactive Stock Charts</div>',unsafe_allow_html=True)
    sym_list = [f"{info['name']} ({sym})" for sym,info in SCAN_UNIVERSE.items()]
    selected = st.selectbox("Select stock", sym_list, key="chart_select")
    sel_sym  = selected.split("(")[1].rstrip(")")
    sel_info = SCAN_UNIVERSE[sel_sym]
    chart_df_raw = all_hist.get(sel_sym, pd.DataFrame())
    chart_df_enr = enrich(chart_df_raw)
    sel_row      = rank_df[rank_df["symbol"]==sel_sym].iloc[0] if sel_sym in rank_df["symbol"].values else None

    if sel_row is not None:
        sig=sel_row["signal"]; sc=sel_row["score"]
        sig_c="green" if sig=="BUY NOW" else ("amber" if sig=="WATCH" else "red")
        st.markdown(f"""
        <div class="ctx-card" style="margin-bottom:12px;">
          <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;">
            {score_ring(sc,52)}
            <div>
              <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:800;color:white;">{sel_info['name']}</div>
              <div style="font-size:.8rem;color:var(--muted);">{sel_info['sector']} · ₹{sel_row['ltp']:,.2f}</div>
            </div>
            <span class="pill pill-{sig_c}">{sig}</span>
            <span class="pill pill-blue">{sel_row['setup_type']}</span>
            {fscore_badge(sel_row['f_score'])}
            <div style="font-size:.8rem;color:var(--muted);">RSI <b style="color:white;">{sel_row['rsi']}</b> · Vol <b style="color:white;">{sel_row['vol_ratio']:.1f}x</b> · 52W% <b style="color:white;">{sel_row['52w_pct']:.0f}%</b> · BB Squeeze <b style="color:{'var(--green)' if sel_row['bb_squeeze'] else 'var(--muted)'};">{'🔥 YES' if sel_row['bb_squeeze'] else 'No'}</b></div>
          </div>
          <div style="margin-top:10px;font-size:.82rem;color:var(--muted);">{sel_row['why_selected']}</div>
        </div>""",unsafe_allow_html=True)

    cfig=candlestick_chart(chart_df_raw,sel_sym,sel_info["name"],chart_df_enr)
    if cfig: st.plotly_chart(cfig,use_container_width=True)
    
    # Score history
    hist=load_score_history(sel_sym)
    if not hist.empty:
        st.markdown('<div class="sec-title" style="font-size:.85rem;">Score History</div>',unsafe_allow_html=True)
        shf=score_history_chart(hist)
        if shf: st.plotly_chart(shf,use_container_width=True,config={"displayModeBar":False})

    # Heatmap
    st.markdown('<div class="sec-title">Universe Score Heatmap</div>',unsafe_allow_html=True)
    hmap=returns_heatmap(rank_df)
    if hmap: st.plotly_chart(hmap,use_container_width=True,config={"displayModeBar":False})

# ─────────────────────────────────────────────────────────────
# TAB 2 — INDICES & GLOBAL
# ─────────────────────────────────────────────────────────────
with tabs[2]:
    st.markdown('<div class="sec-title">India Indices</div>',unsafe_allow_html=True)
    idx_cols=st.columns(4)
    for i,(nm,ticker) in enumerate(INDEX_TICKERS.items()):
        dfi=enrich(fetch_hist(ticker,"1y"))
        with idx_cols[i%4]:
            if dfi.empty:
                st.markdown(f'<div class="index-tile"><div class="index-name">{nm}</div><div class="index-price">N/A</div></div>',unsafe_allow_html=True)
            else:
                last_i=dfi.iloc[-1]; prev_i=sf(dfi["Close"].iloc[-2]) if len(dfi)>1 else np.nan
                chg_i=pct_chg(sf(last_i["Close"]),prev_i)
                st.markdown(f"""
                <div class="index-tile">
                  <div class="index-name">{nm}</div>
                  <div class="index-price">{sf(last_i['Close']):,.2f}</div>
                  <div class="index-chg {'up' if chg_i>=0 else 'dn'}">{'▲' if chg_i>=0 else '▼'} {abs(chg_i):.2f}%</div>
                  <div class="index-extra">EMA20 {sf(last_i.get('EMA20',0)):,.0f} · RSI {sf(last_i.get('RSI14',0)):.0f} · Vol {sf(last_i.get('VOL_RATIO',1)):.1f}x</div>
                </div>""",unsafe_allow_html=True)

    st.markdown('<div class="sec-title">Global Snapshot</div>',unsafe_allow_html=True)
    g5=st.columns(5)
    for i,(nm,ticker) in enumerate(GLOBAL_TICKERS.items()):
        q=get_quote(ticker); chg_g=sf(q.get("chg_pct"),0)
        with g5[i%5]:
            st.markdown(f"""
            <div class="index-tile">
              <div class="index-name">{nm}</div>
              <div class="index-price">{sf(q.get('last'),0):,.2f}</div>
              <div class="index-chg {'up' if chg_g>=0 else 'dn'}">{'▲' if chg_g>=0 else '▼'} {abs(chg_g):.2f}%</div>
            </div>""",unsafe_allow_html=True)

    # FII/DII breakdown
    st.markdown('<div class="sec-title">FII / DII Flow</div>',unsafe_allow_html=True)
    f1,f2,f3,f4=st.columns(4)
    for col,label,val in [(f1,"FII Buy",fii_data.get("fii_buy",0)),(f2,"FII Sell",fii_data.get("fii_sell",0)),
                           (f3,"DII Buy",fii_data.get("dii_buy",0)),(f4,"DII Sell",fii_data.get("dii_sell",0))]:
        with col:
            v=sf(val,0); clr="pos" if "buy" in label.lower() else "neg"
            st.markdown(f"""
            <div class="flow-card">
              <div class="flow-label">{label}</div>
              <div class="flow-val {clr}">₹{v:,.0f} Cr</div>
            </div>""",unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB 3 — IDEAS GRID
# ─────────────────────────────────────────────────────────────
with tabs[3]:
    st.markdown('<div class="sec-title">Ideas Table — Sorted by Composite Score</div>',unsafe_allow_html=True)
    show_cols=["symbol","name","sector","signal","confidence","setup_type","score","tech_score",
               "rs_score","sector_score","fund_score","f_score","recent_perf_score","momentum_rank",
               "ltp","target1","target2","profit_pct_1","profit_pct_2","sl","stoploss_pct",
               "rr","rsi","vol_ratio","donchian","bb_squeeze","52w_pct","horizon","why_selected"]
    avail=[c for c in show_cols if c in ideas.columns]
    st.dataframe(ideas[avail] if not ideas.empty else pd.DataFrame(),use_container_width=True,hide_index=True)
    if not ideas.empty:
        csv=ideas[avail].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV",csv,"marketsense_ideas.csv","text/csv")

# ─────────────────────────────────────────────────────────────
# TAB 4 — SECTORS
# ─────────────────────────────────────────────────────────────
with tabs[4]:
    st.markdown('<div class="sec-title">Sector Leaderboard</div>',unsafe_allow_html=True)
    if not sector_df.empty:
        top4=sector_df.head(4); sc4=st.columns(4)
        for col,(_,r) in zip(sc4,top4.iterrows()):
            sc2=r["sector_score"]; clr2="var(--green)" if sc2>=72 else ("var(--amber)" if sc2>=50 else "var(--red)")
            with col:
                st.markdown(f"""
                <div class="sector-card">
                  <div class="sector-name">{r['sector']}</div>
                  <div class="sector-score-display" style="color:{clr2};">{sc2:.1f}</div>
                  {bar_html(sc2,'green' if sc2>=65 else ('amber' if sc2>=50 else 'red'))}
                  <div class="sector-meta">BUY: {int(r['buy_count'])} · Watch: {int(r['watch_count'])} · {int(r['stocks'])} stocks</div>
                </div>""",unsafe_allow_html=True)

        col_r, col_t = st.columns([1,1])
        with col_r:
            st.markdown('<div class="sec-title" style="font-size:.85rem;">Sector Radar</div>',unsafe_allow_html=True)
            sr_fig=sector_radar(sector_df)
            if sr_fig: st.plotly_chart(sr_fig,use_container_width=True,config={"displayModeBar":False})
        with col_t:
            st.markdown('<div class="sec-title" style="font-size:.85rem;">All Sectors</div>',unsafe_allow_html=True)
            st.dataframe(sector_df,use_container_width=True,hide_index=True)

# ─────────────────────────────────────────────────────────────
# TAB 5 — OPTIONS
# ─────────────────────────────────────────────────────────────
with tabs[5]:
    st.markdown('<div class="sec-title">Options Ideas (Bullish CE View)</div>',unsafe_allow_html=True)
    vix_ok=True
    if not vix_raw.empty:
        try: vix_ok=sf(vix_raw["Close"].iloc[-1])<=20
        except: pass
    if regime["label"] not in ["BULLISH","NEUTRAL"] or not vix_ok:
        st.markdown('<div class="warn-strip">Options ideas suspended — VIX elevated or regime not supportive.</div>',unsafe_allow_html=True)
    else:
        opt_rows=[]
        for _,r in ideas.head(6).iterrows():
            ltp2=sf(r["ltp"])
            strike=int(round(ltp2/50)*50) if ltp2>300 else int(round(ltp2/10)*10)
            opt_rows.append({"symbol":r["symbol"],"name":r["name"],"strategy":"Bull Call",
                              "strike":f"{strike} CE","setup":r["setup_type"],
                              "score":r["score"],"view":"Liquid next expiry · enter after spot confirms"})
        if opt_rows:
            st.dataframe(pd.DataFrame(opt_rows),use_container_width=True,hide_index=True)
            st.markdown('<div class="info-strip">⚡ Enter only after spot confirms strength. Keep options ≤2% of capital. Use liquid expiry.</div>',unsafe_allow_html=True)
        else: st.info("No qualifying ideas for options.")

# ─────────────────────────────────────────────────────────────
# TAB 6 — ALERTS
# ─────────────────────────────────────────────────────────────
with tabs[6]:
    st.markdown('<div class="sec-title">Live Alert Engine</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="info-strip">Showing stocks where RSI ≥ {alert_rsi_min} AND Vol ratio ≥ {alert_vol_min}x AND Score ≥ {alert_score_min}. Adjust thresholds in sidebar.</div>',unsafe_allow_html=True)
    if alerts.empty:
        st.info("No stocks currently matching alert criteria. Loosen the thresholds in the sidebar.")
    else:
        for _,r in alerts.iterrows():
            sig3=r["signal"]; sc3=r["score"]
            sig_c3="green" if sig3=="BUY NOW" else ("amber" if sig3=="WATCH" else "red")
            sq3="🔥 BB Squeeze" if r.get("bb_squeeze") else ""
            ew3="⚠️ "+r.get("earning_note","") if r.get("earning_note","") and "no near" not in r.get("earning_note","") else ""
            st.markdown(f"""
            <div class="alert-card">
              <div>
                <div style="font-family:'Syne',sans-serif;font-weight:800;color:white;font-size:.95rem;">{r['name']} ({r['symbol']})</div>
                <div style="font-size:.76rem;color:var(--muted);">{r['sector']} · {r['setup_type']} · {sq3} {ew3}</div>
              </div>
              <div style="text-align:right;">
                <span class="pill pill-{sig_c3}" style="margin-bottom:4px;display:inline-block;">{sig3}</span><br>
                <span style="font-family:'Space Mono',monospace;font-size:.72rem;color:var(--muted);">RSI {r['rsi']} · Vol {r['vol_ratio']:.1f}x · Score {sc3}</span>
              </div>
            </div>""",unsafe_allow_html=True)

    # BB Squeeze alerts specifically
    st.markdown('<div class="sec-title">BB Squeeze Alerts 🔥</div>',unsafe_allow_html=True)
    squeeze_stocks=rank_df[rank_df["bb_squeeze"]==True].sort_values("score",ascending=False)
    if squeeze_stocks.empty:
        st.info("No BB squeeze setups detected currently.")
    else:
        st.markdown('<div class="good-strip">Bollinger Band compression detected — these stocks may be setting up for an explosive move.</div>',unsafe_allow_html=True)
        for _,r in squeeze_stocks.iterrows():
            sig4=r["signal"]; sc4="green" if sig4=="BUY NOW" else ("amber" if sig4=="WATCH" else "red")
            st.markdown(f"""
            <div class="alert-card">
              <div>
                <div style="font-family:'Syne',sans-serif;font-weight:800;color:white;">🔥 {r['name']} ({r['symbol']})</div>
                <div style="font-size:.76rem;color:var(--muted);">{r['sector']} · Score {r['score']} · RSI {r['rsi']} · Vol {r['vol_ratio']:.1f}x</div>
              </div>
              <span class="pill pill-{sc4}">{sig4}</span>
            </div>""",unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB 7 — DEEP DIVE
# ─────────────────────────────────────────────────────────────
with tabs[7]:
    st.markdown('<div class="sec-title">Stock Deep Dive</div>',unsafe_allow_html=True)
    dd_sym_list=[f"{info['name']} ({sym})" for sym,info in SCAN_UNIVERSE.items()]
    dd_sel=st.selectbox("Choose stock for deep dive",dd_sym_list,key="dd_select")
    dd_sym=dd_sel.split("(")[1].rstrip(")")
    dd_info=SCAN_UNIVERSE[dd_sym]
    dd_row=rank_df[rank_df["symbol"]==dd_sym]
    dd_fund=all_fund.get(dd_sym,{})
    dd_hist=all_hist.get(dd_sym,pd.DataFrame())
    dd_enr=enrich(dd_hist)

    if not dd_row.empty:
        r=dd_row.iloc[0]
        # Chart
        dchart=candlestick_chart(dd_hist,dd_sym,dd_info["name"],dd_enr)
        if dchart: st.plotly_chart(dchart,use_container_width=True)
        
        # Metrics grid
        c1,c2,c3,c4=st.columns(4)
        metrics=[
            (c1,"Score",f"{r['score']}","base_score"),
            (c2,"Technical",f"{r['tech_score']}",""),
            (c3,"Fund Score",f"{r['fund_score']}",""),
            (c4,"Piotroski F",f"{r['f_score']}/9",""),
        ]
        for col,lbl,val,_ in metrics:
            with col:
                st.metric(lbl,val)
        
        c5,c6,c7,c8=st.columns(4)
        for col,lbl,val in [(c5,"RSI 14",f"{r['rsi']}"),(c6,"Vol Ratio",f"{r['vol_ratio']:.1f}x"),
                             (c7,"52W Position",f"{r['52w_pct']:.0f}%"),(c8,"BB Squeeze","🔥 YES" if r['bb_squeeze'] else "No")]:
            with col: st.metric(lbl,val)

        # Trade plan
        st.markdown('<div class="sec-title" style="font-size:.85rem;">Trade Plan</div>',unsafe_allow_html=True)
        tp1,tp2=st.columns(2)
        with tp1:
            st.markdown(f"""
            <div class="sizer-card">
              <div class="sizer-title">📋 {r['name']} — {r['signal']}</div>
              <div class="sizer-row"><span class="sk">Setup</span><span class="sv">{r['setup_type']}</span></div>
              <div class="sizer-row"><span class="sk">Entry (LTP)</span><span class="sv">₹{r['ltp']:,.2f}</span></div>
              <div class="sizer-row"><span class="sk">Target 1</span><span class="sv" style="color:var(--green);">₹{r['target1']:,.2f} (+{r['profit_pct_1']}%)</span></div>
              <div class="sizer-row"><span class="sk">Target 2</span><span class="sv" style="color:var(--green);">₹{r['target2']:,.2f} (+{r['profit_pct_2']}%)</span></div>
              <div class="sizer-row"><span class="sk">Stop Loss</span><span class="sv" style="color:var(--red);">₹{r['sl']:,.2f} (-{r['stoploss_pct']}%)</span></div>
              <div class="sizer-row"><span class="sk">Risk:Reward</span><span class="sv">{r['rr']}</span></div>
              <div class="sizer-row"><span class="sk">Horizon</span><span class="sv">{r['horizon']}</span></div>
              <div class="sizer-row"><span class="sk">Earnings note</span><span class="sv">{r['earning_note']}</span></div>
            </div>""",unsafe_allow_html=True)
        with tp2:
            st.markdown(f"""
            <div class="sizer-card">
              <div class="sizer-title">📊 Fundamentals</div>
              <div class="sizer-row"><span class="sk">Revenue Growth</span><span class="sv">{sf(dd_fund.get('revenue_growth',0))*100:.1f}%</span></div>
              <div class="sizer-row"><span class="sk">Earnings Growth</span><span class="sv">{sf(dd_fund.get('earnings_growth',0))*100:.1f}%</span></div>
              <div class="sizer-row"><span class="sk">ROE</span><span class="sv">{sf(dd_fund.get('roe',0))*100:.1f}%</span></div>
              <div class="sizer-row"><span class="sk">Profit Margin</span><span class="sv">{sf(dd_fund.get('profit_margin',0))*100:.1f}%</span></div>
              <div class="sizer-row"><span class="sk">Debt/Equity</span><span class="sv">{sf(dd_fund.get('debt_to_equity',0)):.2f}</span></div>
              <div class="sizer-row"><span class="sk">Trailing PE</span><span class="sv">{sf(dd_fund.get('trailing_pe',0)):.1f}</span></div>
              <div class="sizer-row"><span class="sk">PEG Ratio</span><span class="sv">{sf(dd_fund.get('peg_ratio',0)):.2f}</span></div>
              <div class="sizer-row"><span class="sk">Current Ratio</span><span class="sv">{sf(dd_fund.get('current_ratio',0)):.2f}</span></div>
            </div>""",unsafe_allow_html=True)

        # Piotroski detail
        fs_det=dd_fund.get("f_score_detail",{})
        if fs_det:
            st.markdown('<div class="sec-title" style="font-size:.85rem;">Piotroski F-Score Detail</div>',unsafe_allow_html=True)
            all_checks=["ROE+","CFO+","∆ROA+","CFO>ROA","Debt↓","Liquid+","Rev↑","Margin↑","EPS↑"]
            fs_cols=st.columns(len(all_checks))
            for col,chk in zip(fs_cols,all_checks):
                passed=chk in fs_det
                with col:
                    st.markdown(f'<div style="text-align:center;font-size:.68rem;color:var(--muted);margin-bottom:4px;">{chk}</div><div style="text-align:center;font-size:1.1rem;">{"✅" if passed else "❌"}</div>',unsafe_allow_html=True)

        # Why selected
        st.markdown('<div class="sec-title" style="font-size:.85rem;">Why Selected</div>',unsafe_allow_html=True)
        st.markdown(f'<div class="ctx-card"><div class="ctx-body">{r["why_selected"]}</div></div>',unsafe_allow_html=True)

        # Score history
        hist_d=load_score_history(dd_sym)
        if not hist_d.empty:
            st.markdown('<div class="sec-title" style="font-size:.85rem;">Score History</div>',unsafe_allow_html=True)
            shf2=score_history_chart(hist_d)
            if shf2: st.plotly_chart(shf2,use_container_width=True,config={"displayModeBar":False})

# ─────────────────────────────────────────────────────────────
# TAB 8 — ECONOMIC CALENDAR
# ─────────────────────────────────────────────────────────────
with tabs[8]:
    st.markdown('<div class="sec-title">Economic & Event Calendar</div>',unsafe_allow_html=True)
    today_d=datetime.now(IST).date()
    cal_df=pd.DataFrame(ECONOMIC_CALENDAR)
    cal_df["date_parsed"]=pd.to_datetime(cal_df["date"]).dt.date
    cal_df["days_away"]=(cal_df["date_parsed"]-today_d).apply(lambda x: x.days)
    cal_df=cal_df.sort_values("date_parsed")
    upcoming=cal_df[cal_df["days_away"]>=0]
    past=cal_df[cal_df["days_away"]<0]
    st.markdown(f'<div class="info-strip">📅 Today: {today_d.strftime("%d %b %Y")} · {len(upcoming)} upcoming events</div>',unsafe_allow_html=True)
    for _,r in upcoming.iterrows():
        imp=r["impact"]
        imp_cls=f"cal-impact-{imp}"
        strip_cls="warn-strip" if imp=="HIGH" else ("amber-strip" if imp=="MEDIUM" else "info-strip")
        st.markdown(f"""
        <div class="{strip_cls}" style="margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
          <div>
            <span class="{imp_cls}">{imp}</span>
            <b style="margin-left:8px;">{r['event']}</b>
            <span style="font-size:.75rem;color:var(--muted);margin-left:8px;">{r['sector']}</span>
          </div>
          <div style="text-align:right;font-family:'Space Mono',monospace;font-size:.72rem;">
            {r['date']} · <b>{r['days_away']}d away</b>
          </div>
        </div>""",unsafe_allow_html=True)
    if not past.empty:
        with st.expander("Past events"):
            for _,r in past.iterrows():
                st.markdown(f'<div style="font-size:.8rem;color:var(--muted);padding:4px 0;">{r["date"]} · {r["event"]}</div>',unsafe_allow_html=True)

    # NSE holidays
    st.markdown('<div class="sec-title">NSE Trading Holidays</div>',unsafe_allow_html=True)
    if holiday_df.empty:
        st.info("Could not load NSE holiday data.")
    else:
        hol_upcoming=holiday_df[holiday_df["date"]>=today_d]
        for _,r in hol_upcoming.iterrows():
            d_away=(r["date"]-today_d).days
            st.markdown(f'<div class="info-strip" style="margin-bottom:4px;"><b>{r["date"].strftime("%d %b %Y")}</b> — {r["holiday"]} <span style="float:right;opacity:.6;">{d_away} days away</span></div>',unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# TAB 9 — FULL SCAN
# ─────────────────────────────────────────────────────────────
with tabs[9]:
    st.markdown('<div class="sec-title">Complete Universe Ranking</div>',unsafe_allow_html=True)
    all_cols=["symbol","name","sector","signal","confidence","setup_type","score","tech_score",
              "rs_score","sector_score","fund_score","f_score","recent_perf_score","momentum_rank",
              "ltp","target1","target2","profit_pct_1","profit_pct_2","sl","stoploss_pct",
              "rr","rsi","vol_ratio","donchian","bb_squeeze","52w_pct","horizon"]
    avail_all=[c for c in all_cols if c in rank_df.columns]
    st.dataframe(rank_df[avail_all],use_container_width=True,hide_index=True)
    csv_full=rank_df[avail_all].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Full Scan CSV",csv_full,"marketsense_full_scan.csv","text/csv")

# ─────────────────────────────────────────────────────────────
# TAB 10 — NEWS
# ─────────────────────────────────────────────────────────────
with tabs[10]:
    col_g,col_i=st.columns(2)
    with col_g:
        st.markdown('<div class="sec-title">Global & US Macro</div>',unsafe_allow_html=True)
        gn=news_df_raw[news_df_raw["bucket"].isin(["global_macro","us_policy"])].head(15)
        if gn.empty: st.info("No global news.")
        else:
            for _,r in gn.iterrows():
                cls="ns-pos" if r["score"]>0 else ("ns-neg" if r["score"]<0 else "ns-neu")
                st.markdown(f"""
                <div class="news-row">
                  <div class="news-score {cls}">{r['score']:+d}</div>
                  <div>
                    <div class="news-title"><a href="{r['link']}" target="_blank" style="color:inherit;text-decoration:none;">{r['title'][:100]}</a></div>
                    <div class="news-meta">{r['source']} · {r['sector_tags'][:50]}</div>
                  </div>
                </div>""",unsafe_allow_html=True)
    with col_i:
        st.markdown('<div class="sec-title">India Markets & Policy</div>',unsafe_allow_html=True)
        ine=news_df_raw[news_df_raw["bucket"].isin(["india_market","govt_policy","rbi_policy"])].head(15)
        if ine.empty: st.info("No India news.")
        else:
            for _,r in ine.iterrows():
                cls="ns-pos" if r["score"]>0 else ("ns-neg" if r["score"]<0 else "ns-neu")
                st.markdown(f"""
                <div class="news-row">
                  <div class="news-score {cls}">{r['score']:+d}</div>
                  <div>
                    <div class="news-title"><a href="{r['link']}" target="_blank" style="color:inherit;text-decoration:none;">{r['title'][:100]}</a></div>
                    <div class="news-meta">{r['source']} · {r['sector_tags'][:50]}</div>
                  </div>
                </div>""",unsafe_allow_html=True)

    p_col,n_col=st.columns(2)
    with p_col:
        st.markdown('<div class="sec-title">Top Positive</div>',unsafe_allow_html=True)
        for h in nb.get("top_positive",[])[:5]:
            st.markdown(f'<div class="good-strip" style="margin-bottom:4px;font-size:.79rem;">{h[:120]}</div>',unsafe_allow_html=True)
    with n_col:
        st.markdown('<div class="sec-title">Top Negative</div>',unsafe_allow_html=True)
        for h in nb.get("top_negative",[])[:5]:
            st.markdown(f'<div class="warn-strip" style="margin-bottom:4px;font-size:.79rem;">{h[:120]}</div>',unsafe_allow_html=True)

# ============================================================
# FOOTER
# ============================================================
st.markdown("""
<div style="margin-top:2.5rem;padding:1rem 0;border-top:1px solid rgba(255,255,255,0.06);
text-align:center;font-family:'Space Mono',monospace;font-size:.66rem;color:#4d5470;">
MARKETSENSE PRO v6 · Probability-based research tool · NOT investment advice ·
Apply strict position sizing and stop-losses · Past signals ≠ future results
</div>""",unsafe_allow_html=True)
