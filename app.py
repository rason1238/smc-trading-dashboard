import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="DAZIR SMC SNIPER", page_icon="🎯", layout="wide")

st.title("🎯 DAZIR SMC SNIPER V4")
st.markdown("### رادار الصفقات الفوري - Smart Money Concepts")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT"]

@st.cache_data(ttl=60)
def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=["t","o","h","l","c","v","ct","qv","n","tbv","tqv","i"])
        df["c"] = df["c"].astype(float)
        df["h"] = df["h"].astype(float)
        df["l"] = df["l"].astype(float)
        return df
    except:
        return None

def analyze_symbol(symbol):
    df = get_klines(symbol)
    if df is None or len(df) < 50:
        return None
    current = df["c"].iloc[-1]
    recent_high = df["h"].iloc[-20:].max()
    recent_low = df["l"].iloc[-20:].min()
    delta = df["c"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    score = 50
    if rsi < 30:
        score += 20
    if rsi > 70:
        score -= 20
    if current < recent_low * 1.02:
        score += 15
    if current > recent_high * 0.98:
        score -= 15
    if score >= 65:
        direction = "شراء"
        signal = "🟢"
    elif score <= 35:
        direction = "بيع"
        signal = "🔴"
    else:
        direction = "محايد"
        signal = "⚪"
    return {
        "symbol": symbol,
        "price": round(current, 2),
        "direction": direction,
        "signal": signal,
        "score": round(score, 1),
        "rsi": round(rsi, 1)
    }

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("⏱️ وقت التحديث", datetime.now().strftime("%H:%M:%S"))
with col2:
    session = "لندن/نيويورك" if 7 <= datetime.now().hour < 20 else "آسيا"
    st.metric("🌍 جلسة السوق", session)
with col3:
    st.metric("📊 العملات", len(SYMBOLS))

st.divider()

if st.button("🔍 تحديث وتحليل السوق الآن", use_container_width=True):
    with st.spinner("جاري تحليل العملات..."):
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(analyze_symbol, s) for s in SYMBOLS]
            for f in futures:
                res = f.result()
                if res:
                    results.append(res)
        results.sort(key=lambda x: x["score"], reverse=True)
        if results:
            best = results[0]
            st.success(f"### 🏆 أفضل صفقة: {best['symbol']} - {best['direction']} {best['signal']}")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("💰 السعر الحالي", f"{best['price']}$")
            with col_b:
                st.metric("💪 قوة الإشارة", f"{best['score']}%")
            with col_c:
                st.metric("📊 RSI", f"{best['rsi']}")
            st.divider()
            st.subheader("📊 جميع الصفقات المرشحة")
            df_results = pd.DataFrame(results)
            df_results = df_results[["signal", "symbol", "price", "direction", "score", "rsi"]]
            df_results.columns = ["", "العملة", "السعر", "الاتجاه", "القوة%", "RSI"]
            st.dataframe(df_results, use_container_width=True, height=400)
        else:
            st.error("لا توجد بيانات حالياً")
else:
    st.info("💡 اضغط على زر التحديث لبدء البحث عن الفرص")

st.divider()
st.caption("⚠️ الإشارات للعرض فقط - طبق نظام إدارة المخاطرة الخاص بك")
