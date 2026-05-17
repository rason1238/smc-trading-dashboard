import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== إعدادات الصفحة ====================
st.set_page_config(
    page_title="DAZIR SMC SNIPER V4",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== قائمة العملات ====================
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT",
    "MATICUSDT", "UNIUSDT", "ATOMUSDT", "LTCUSDT", "NEARUSDT"
]

# ==================== إعدادات API ====================
BINANCE_API = "https://api.binance.com/api/v3"
TIMEFRAME = "15m"
LIMIT = 100

# ==================== دوال التحليل ====================
def get_klines(symbol, interval=TIMEFRAME, limit=LIMIT):
    url = f"{BINANCE_API}/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        df = pd.DataFrame(data, columns=["t","o","h","l","c","v","ct","qv","n","tbv","tqv","i"])
        df["o"] = df["o"].astype(float)
        df["h"] = df["h"].astype(float)
        df["l"] = df["l"].astype(float)
        df["c"] = df["c"].astype(float)
        df["v"] = df["v"].astype(float)
        df["time"] = pd.to_datetime(df["t"], unit='ms')
        return df
    except:
        return None

def calculate_rsi(df, period=14):
    delta = df["c"].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_macd(df):
    exp1 = df["c"].ewm(span=12, adjust=False).mean()
    exp2 = df["c"].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd.iloc[-1], signal.iloc[-1]

def calculate_support_resistance(df):
    recent_high = df["h"].iloc[-20:].max()
    recent_low = df["l"].iloc[-20:].min()
    return recent_high, recent_low

def analyze_symbol(symbol):
    df = get_klines(symbol)
    if df is None or len(df) < 50:
        return None
    
    current_price = df["c"].iloc[-1]
    rsi = calculate_rsi(df)
    macd, signal = calculate_macd(df)
    resistance, support = calculate_support_resistance(df)
    
    # حساب قوة الإشارة
    score = 50  # أساس
    reasons = []
    
    if rsi < 30:
        score += 15
        reasons.append("RSI منخفض (تشبع بيع)")
    elif rsi > 70:
        score -= 15
        reasons.append("RSI مرتفع (تشبع شراء)")
    
    if macd > signal:
        score += 10
        reasons.append("MACD إيجابي")
    else:
        score -= 10
        reasons.append("MACD سلبي")
    
    if current_price < support * 1.02:
        score += 10
        reasons.append("قريب من الدعم")
    elif current_price > resistance * 0.98:
        score -= 10
        reasons.append("قريب من المقاومة")
    
    # تحديد القرار
    if score >= 65:
        direction = "شراء"
        sl = support * 0.98
        tp = resistance * 0.98
        signal_type = "🟢"
    elif score <= 35:
        direction = "بيع"
        sl = resistance * 1.02
        tp = support * 1.02
        signal_type = "🔴"
    else:
        direction = "محايد"
        sl = current_price
        tp = current_price
        signal_type = "⚪"
    
    # حساب RR
    risk = abs(current_price - sl) if sl != current_price else 0.001
    reward = abs(tp - current_price) if tp != current_price else 0.001
    rr = round(reward / risk, 2) if risk > 0 else 0
    
    return {
        "symbol": symbol,
        "price": round(current_price, 4),
        "direction": direction,
        "signal": signal_type,
        "score": round(score, 1),
        "rr": rr,
        "sl": round(sl, 4),
        "tp": round(tp, 4),
        "rsi": round(rsi, 1),
        "reasons": reasons[:3]
    }

# ==================== واجهة التطبيق ====================
st.title("🎯 DAZIR SMC SNIPER V4")
st.markdown("### رادار الصفقات الفوري - Smart Money Concepts")

# أعمدة المعلومات
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("⏱️ وقت التحديث", datetime.now().strftime("%H:%M:%S"))
with col2:
    session = "لندن/نيويورك" if 7 <= datetime.now().hour < 20 else "آسيا"
    st.metric("🌍 جلسة السوق", session)
with col3:
    st.metric("📊 العملات المحللة", len(SYMBOLS))

st.divider()

# زر التحديث
if st.button("🔍 تحديث وتحليل السوق الآن", use_container_width=True):
    with st.spinner("جاري تحليل العملات..."):
        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(analyze_symbol, s): s for s in SYMBOLS}
            for future in as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
        
        # ترتيب النتائج حسب القوة
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # عرض أفضل صفقة
        if results:
            best = results[0]
            st.success(f"### 🏆 أفضل صفقة حالياً: {best['symbol']}")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("💰 السعر الحالي", f"{best['price']}$")
                st.metric("📈 القرار", f"{best['signal']} {best['direction']}")
                st.metric("💪 قوة الإشارة", f"{best['score']}%")
            with col_b:
                st.metric("📊 نسبة المخاطرة (RR)", f"1:{best['rr']}")
                st.metric("🛡️ وقف الخسارة", f"{best['sl']}$")
                st.metric("🎯 الهدف", f"{best['tp']}$")
            
            st.info(f"📋 أسباب القوة: {', '.join(best['reasons'])}")
        
        # عرض جدول جميع الصفقات
        st.divider()
        st.subheader("📊 جميع الصفقات المرشحة")
        
        df_results = pd.DataFrame(results)
        df_results = df_results[["signal", "symbol", "price", "direction", "score", "rr", "rsi"]]
        df_results.columns = ["إشارة", "العملة", "السعر", "الاتجاه", "القوة%", "RR", "RSI"]
        
        st.dataframe(df_results, use_container_width=True, height=400)

else:
    st.info("💡 اضغط على زر 'تحديث وتحليل السوق الآن' لبدء البحث عن الفرص")

st.divider()
st.caption("⚠️ الإشارات للعرض فقط - طبق نظام إدارة المخاطرة الخاص بك")
