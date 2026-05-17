import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="DAZIR SMC SNIPER PRO", page_icon="🎯", layout="wide")

# Styling adjustments for high-end look
st.markdown("""
    <style>
    .metric-card { background-color: #1e2430; padding: 15px; border-radius: 10px; border: 1px solid #2d3748; }
    .buy-signal { color: #00ff88; font-weight: bold; }
    .sell-signal { color: #ff3366; font-weight: bold; }
    .neutral-signal { color: #a0aec0; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 DAZIR SMC SNIPER V5 PRO")
st.markdown("### رادار الصفقات الفوري والمتقدم - Smart Money Concepts Institutional System")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "LINKUSDT", "AVAXUSDT"]
TIMEFRAMES = {"15m": "15m", "1h": "1h", "4h": "4h"}

@st.cache_data(ttl=60)
def fetch_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return pd.DataFrame()
        data = r.json()
        df = pd.DataFrame(data, columns=["t","o","h","l","c","v","ct","qv","n","tbv","tqv","i"])
        df = df.astype({
            "o": float, "h": float, "l": float, "c": float, "v": float, "qv": float
        })
        df["t"] = pd.to_datetime(df["t"], unit="ms")
        return df
    except Exception:
        return pd.DataFrame()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["h"]
    low = df["l"]
    close_prev = df["c"].shift(1)
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def extract_smc_metrics(df: pd.DataFrame):
    if len(df) < 50:
        return {"structure": "NEUTRAL", "bos": False, "liquidity_hi": 0.0, "liquidity_lo": 0.0, "sup": 0.0, "res": 0.0}
    
    recent_h = df["h"].iloc[-20:].max()
    recent_l = df["l"].iloc[-20:].min()
    
    # Simple fractal-based support and resistance mapping
    supports = df["l"].rolling(window=10, center=True).min()
    resistances = df["h"].rolling(window=10, center=True).max()
    sup = supports.dropna().iloc[-1] if not supports.dropna().empty else recent_l
    res = resistances.dropna().iloc[-1] if not resistances.dropna().empty else recent_h

    # Shift calculations to determine structure breaks
    prev_h = df["h"].iloc[-40:-20].max()
    prev_l = df["l"].iloc[-40:-20].min()
    last_close = df["c"].iloc[-1]
    
    bos = False
    structure = "NEUTRAL"
    
    if last_close > prev_h:
        structure = "BULLISH"
        bos = True
    elif last_close < prev_l:
        structure = "BEARISH"
        bos = True
    elif last_close > (prev_h + prev_l) / 2:
        structure = "BULLISH"
    else:
        structure = "BEARISH"

    return {
        "structure": structure,
        "bos": bos,
        "liquidity_hi": recent_h,
        "liquidity_lo": recent_l,
        "sup": sup,
        "res": res
    }

def analyze_symbol(symbol: str) -> dict:
    # 1. Fetch Multi-Timeframe Data
    df_15m = fetch_klines(symbol, TIMEFRAMES["15m"], 200)
    df_1h = fetch_klines(symbol, TIMEFRAMES["1h"], 200)
    df_4h = fetch_klines(symbol, TIMEFRAMES["4h"], 200)
    
    if df_15m.empty or df_1h.empty or df_4h.empty:
        return None
    
    # 2. Indicators Definition (15m execution frame)
    close_15m = df_15m["c"]
    current_price = close_15m.iloc[-1]
    
    ema50 = close_15m.ewm(span=50, adjust=False).mean().iloc[-1]
    ema200 = close_15m.ewm(span=200, adjust=False).mean().iloc[-1]
    
    rsi_series = calculate_rsi(close_15m, 14)
    rsi_val = rsi_series.iloc[-1]
    rsi_sma = rsi_series.rolling(7).mean().iloc[-1] # Multi-layered RSI check
    
    atr = calculate_atr(df_15m, 14).iloc[-1]
    
    # Volume spike detection
    vol_mean = df_15m["v"].rolling(20).mean().iloc[-1]
    curr_vol = df_15m["v"].iloc[-1]
    vol_spike = curr_vol > (vol_mean * 1.8)

    # 3. Smart Money Concepts Extraction
    smc_15m = extract_smc_metrics(df_15m)
    smc_1h = extract_smc_metrics(df_1h)
    smc_4h = extract_smc_metrics(df_4h)
    
    # 4. Multi-Timeframe Scoring Metrics
    score = 50
    confirmations = []
    
    # Trend Rule (4H Macro Alignment)
    if smc_4h["structure"] == "BULLISH" and current_price > ema200:
        score += 15
        confirmations.append("4H Bullish Trend Alignment")
    elif smc_4h["structure"] == "BEARISH" and current_price < ema200:
        score -= 15
        confirmations.append("4H Bearish Trend Alignment")

    # Structure Rules (1H Confirmation Framework)
    if smc_1h["structure"] == "BULLISH":
        score += 10
    else:
        score -= 10
        
    if smc_1h["bos"]:
        score += 5 if smc_1h["structure"] == "BULLISH" else -5

    # 15m Tactical Execution Level Rules
    if smc_15m["bos"] and smc_15m["structure"] == "BULLISH":
        score += 10
        confirmations.append("15m Break of Structure (BOS)")
    elif smc_15m["bos"] and smc_15m["structure"] == "BEARISH":
        score -= 10
        confirmations.append("15m Break of Structure (BOS)")

    # Advanced RSI Evaluation
    if rsi_val < 32 and rsi_val > rsi_sma: # Turning up from oversold
        score += 15
        confirmations.append("RSI Out of Oversold Engine")
    elif rsi_val > 68 and rsi_val < rsi_sma: # Turning down from overbought
        score -= 15
        confirmations.append("RSI Out of Overbought Engine")

    # Volatility Check
    if vol_spike:
        score += 5 if score > 50 else -5
        confirmations.append("High-Volume Injection Identified")

    # Clamp logic
    score = max(0, min(100, score))
    
    # Direction Definition mapping
    if score >= 62:
        direction, signal, color = "شراء (LONG)", "🟢 BUY", "buy-signal"
    elif score <= 38:
        direction, signal, color = "بيع (SHORT)", "🔴 SELL", "sell-signal"
    else:
        direction, signal, color = "محايد (HOLD)", "⚪ NEUTRAL", "neutral-signal"

    # 5. Risk Mitigation Metrics calculations
    if "LONG" in direction:
        stop_loss = current_price - (atr * 1.5)
        take_profit1 = current_price + (atr * 1.5)
        take_profit2 = current_price + (atr * 3.0)
    else:
        stop_loss = current_price + (atr * 1.5)
        take_profit1 = current_price - (atr * 1.5)
        take_profit2 = current_price - (atr * 3.0)
        
    risk_reward = abs(take_profit1 - current_price) / max(1e-5, abs(current_price - stop_loss))

    return {
        "symbol": symbol,
        "price": round(current_price, 4 if current_price < 1.0 else 2),
        "direction": direction,
        "signal": signal,
        "color": color,
        "score": round(score, 1),
        "rsi": round(rsi_val, 1),
        "atr": round(atr, 4),
        "sl": round(stop_loss, 4 if current_price < 1.0 else 2),
        "tp1": round(take_profit1, 4 if current_price < 1.0 else 2),
        "tp2": round(take_profit2, 4 if current_price < 1.0 else 2),
        "rr": round(risk_reward, 2),
        "conf": ", ".join(confirmations) if confirmations else "No strong metrics"
    }

def run_market_scanner():
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(analyze_symbol, s) for s in SYMBOLS]
        for f in futures:
            res = f.result()
            if res:
                results.append(res)
    return results

# Top System Bar
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("⏱️ آخر تحديث للمنظومة", datetime.now().strftime("%H:%M:%S"))
with col2:
    session = "لندن / نيويورك" if 7 <= datetime.now().hour < 21 else "آسيا"
    st.metric("🌍 الجلسة الحالية المعترف بها", session)
with col3:
    st.metric("📊 مجموع الأصول المراقبة", len(SYMBOLS))

st.divider()

if st.button("🔍 تشغيل الرادار ومسح السيولة المؤسسية", use_container_width=True):
    with st.spinner("جاري سحب البيانات وتحليل السيولة والأنماط المعقدة..."):
        data_payload = run_market_scanner()
        
        if data_payload:
            # Sort system by absolute distance to extremity signals
            data_payload.sort(key=lambda x: abs(x["score"] - 50), reverse=True)
            top_asset = data_payload[0]
            
            # High-Grade Alert Module
            st.success(f"### 🏆 الإشارة الأكثر تأكيداً الآن: {top_asset['symbol']} ({top_asset['signal']})")
            
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("السعر الحالي", f"${top_asset['price']}")
            with m_col2:
                st.metric("قوة التأكيد الهيكلي", f"{top_asset['score']}%")
            with m_col3:
                st.metric("معدل العائد للمخاطرة R:R", f"{top_asset['rr']}")
            with m_col4:
                st.metric("مؤشر Volatility ATR", f"{top_asset['atr']}")
                
            # Engine Execution Parameters Card
            st.markdown(f"""
            <div class='metric-card'>
                <h4>🎯 معطيات إدارة المخاطر المقترحة للـ {top_asset['symbol']}</h4>
                <p><b>نقطة الدخول الحالية:</b> {top_asset['price']}</p>
                <p style='color: #ff3366;'><b>وقف الخسارة الحتمي (SL):</b> {top_asset['sl']}</p>
                <p style='color: #00ff88;'><b>الهدف الأول المقترح (TP1):</b> {top_asset['tp1']}</p>
                <p style='color: #00ffbb;'><b>الهدف الثاني الاستراتيجي (TP2):</b> {top_asset['tp2']}</p>
                <p><b>التأكيدات المرصودة:</b> {top_asset['conf']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
            st.subheader("📊 لوحة الرادار الشاملة لجميع العملات")
            
            # Formulating deployment dataframe cleanly
            df_view = pd.DataFrame(data_payload)
            df_view = df_view[["signal", "symbol", "price", "score", "rsi", "sl", "tp1", "tp2", "rr", "conf"]]
            df_view.columns = ["الإشارة", "الرمز", "السعر الحالي", "قوة الإشارة %", "RSI 15m", "وقف الخسارة SL", "الهدف 1", "الهدف 2", "العائد:المخاطرة", "موجز التأكيدات"]
            
            st.dataframe(df_view.style.background_gradient(subset=["قوة الإشارة %"], cmap="coolwarm"), use_container_width=True, height=450)
            
        else:
            st.error("فشل النظام في استرداد وتوليد تحليلات دقيقة للسوق حالياً. تحقق من اتصالك بمزود البيانات.")
else:
    st.info("💡 النظام في وضع الاستعداد الآن. يرجى الضغط على زر التحديث في الأعلى لتشغيل خوارزميات SMC المتقدمة ومسح الأسواق.")

st.divider()
st.caption("⚠️ نظام التحليلات الآلي مبني بالكامل على مؤشرات الخوارزميات الفنية وذكاء الهياكل السعرية. التداول يحتوي على مخاطر خسارة أموالك، ولا يمثل هذا التطبيق توصية مالية مباشرة.")
