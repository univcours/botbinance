import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime
import numpy as np
import json

# ====================== إعدادات الصفحة ======================
st.set_page_config(
    page_title="Gold Trading Bot - Signals",
    page_icon="📊",
    layout="wide"
)

# ====================== دوال جلب البيانات ======================
@st.cache_data(ttl=30)
def get_klines(symbol="XAUUSDT", interval="1m", limit=200):
    """جلب بيانات الشموع من Binance Futures"""
    
    # استخدام proxy لتجنب مشاكل CORS
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v1/klines"
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    try:
        # إضافة headers لتجنب الحظر
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }
        
        response = requests.get(
            base_url + endpoint, 
            params=params, 
            headers=headers,
            timeout=15
        )
        
        if response.status_code != 200:
            st.warning(f"⚠️ Binance API error: {response.status_code}")
            # محاولة استخدام API بديل
            return get_klines_alternative(symbol, interval, limit)
            
        data = response.json()
        
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    except Exception as e:
        st.warning(f"⚠️ Binance API error: {str(e)}")
        # محاولة استخدام API بديل
        return get_klines_alternative(symbol, interval, limit)

def get_klines_alternative(symbol="XAUUSDT", interval="1m", limit=200):
    """API بديل لجلب البيانات (في حالة فشل Binance)"""
    try:
        # استخدام Binance Public API مع endpoint مختلف
        url = "https://api.binance.com/api/v3/klines"
        
        params = {
            "symbol": symbol.replace("USDT", "USDT"),  # تأكد من الرمز
            "interval": interval,
            "limit": limit
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            # استخدام بيانات تجريبية
            return generate_mock_data(limit)
            
        data = response.json()
        
        if not data:
            return generate_mock_data(limit)
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    except Exception as e:
        return generate_mock_data(limit)

def generate_mock_data(limit=200):
    """توليد بيانات تجريبية للاختبار"""
    st.info("ℹ️ Using simulated data (API unavailable)")
    
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='1min')
    
    # توليد أسعار عشوائية
    base_price = 3300 + np.random.randn() * 50
    prices = []
    
    for i in range(limit):
        change = np.random.randn() * 2
        base_price += change
        prices.append(base_price)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 2) for p in prices],
        'low': [p - abs(np.random.randn() * 2) for p in prices],
        'close': [p + np.random.randn() * 1.5 for p in prices],
        'volume': [np.random.randint(100, 1000) for _ in range(limit)]
    })
    
    return df

@st.cache_data(ttl=10)
def get_order_book(symbol="XAUUSDT", limit=50):
    """جلب الأوردر بوك"""
    try:
        base_url = "https://fapi.binance.com"
        endpoint = "/fapi/v1/depth"
        
        params = {
            "symbol": symbol,
            "limit": limit
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        
        response = requests.get(base_url + endpoint, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return generate_mock_order_book(limit)
            
        data = response.json()
        
        if not data or 'bids' not in data or 'asks' not in data:
            return generate_mock_order_book(limit)
        
        bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
        asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
        
        return bids, asks
    
    except Exception as e:
        return generate_mock_order_book(limit)

def generate_mock_order_book(limit=50):
    """توليد بيانات تجريبية للأوردر بوك"""
    base_price = 3300
    
    bids = pd.DataFrame({
        'price': [base_price - i * 0.5 for i in range(limit)],
        'quantity': [np.random.randint(10, 100) for _ in range(limit)]
    })
    
    asks = pd.DataFrame({
        'price': [base_price + i * 0.5 for i in range(limit)],
        'quantity': [np.random.randint(10, 100) for _ in range(limit)]
    })
    
    return bids, asks

# ====================== المؤشرات والإشارات ======================
def calculate_indicators(df):
    """حساب المؤشرات الفنية"""
    
    if df.empty or len(df) < 20:
        return df
    
    # المتوسطات المتحركة
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal']
    
    # Bollinger Bands
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['STD_20'] = df['close'].rolling(20).std()
    df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)
    
    return df

def generate_trading_signals(df):
    """توليد إشارات التداول"""
    
    signals = {
        'buy': [],
        'sell': [],
        'strong_buy': [],
        'strong_sell': [],
        'neutral': [],
        'score': 0,
        'reasons': []
    }
    
    if df.empty or len(df) < 50:
        signals['neutral'].append("⏸️ Insufficient data for signals")
        return signals
    
    df = calculate_indicators(df)
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    score = 0
    
    # RSI
    if 'RSI' in last and not pd.isna(last['RSI']):
        if last['RSI'] < 30:
            score += 2
            signals['buy'].append(f"RSI Oversold: {last['RSI']:.2f}")
            signals['reasons'].append(f"🟢 RSI oversold at {last['RSI']:.2f}")
        elif last['RSI'] > 70:
            score -= 2
            signals['sell'].append(f"RSI Overbought: {last['RSI']:.2f}")
            signals['reasons'].append(f"🔴 RSI overbought at {last['RSI']:.2f}")
    
    # MACD
    if 'MACD' in last and 'Signal' in last and not pd.isna(last['MACD']):
        if last['MACD'] > last['Signal']:
            score += 1
            signals['buy'].append("MACD Bullish")
            signals['reasons'].append("🟢 MACD above signal line")
        else:
            score -= 1
            signals['sell'].append("MACD Bearish")
            signals['reasons'].append("🔴 MACD below signal line")
    
    # Bollinger Bands
    if 'Lower_Band' in last and 'Upper_Band' in last:
        if not pd.isna(last['Lower_Band']) and not pd.isna(last['Upper_Band']):
            if last['close'] < last['Lower_Band']:
                score += 2
                signals['buy'].append("Price below Lower Band")
                signals['reasons'].append("🟢 Price below lower Bollinger Band")
            elif last['close'] > last['Upper_Band']:
                score -= 2
                signals['sell'].append("Price above Upper Band")
                signals['reasons'].append("🔴 Price above upper Bollinger Band")
    
    # SMA
    if 'SMA_20' in last and 'SMA_50' in last:
        if not pd.isna(last['SMA_20']) and not pd.isna(last['SMA_50']):
            if last['SMA_20'] > last['SMA_50']:
                score += 1
                signals['buy'].append("SMA 20 > SMA 50 (Bullish)")
                signals['reasons'].append("🟢 SMA 20 above SMA 50")
            else:
                score -= 1
                signals['sell'].append("SMA 20 < SMA 50 (Bearish)")
                signals['reasons'].append("🔴 SMA 20 below SMA 50")
    
    # تحديد قوة الإشارة
    signals['score'] = score
    
    if score >= 5:
        signals['strong_buy'].append(f"🔥 STRONG BUY (Score: {score})")
    elif score >= 2:
        signals['buy'].append(f"📈 BUY (Score: {score})")
    elif score <= -5:
        signals['strong_sell'].append(f"🔥 STRONG SELL (Score: {score})")
    elif score <= -2:
        signals['sell'].append(f"📉 SELL (Score: {score})")
    else:
        signals['neutral'].append(f"⏸️ NEUTRAL (Score: {score})")
    
    return signals

# ====================== عرض الإشارات ======================
def display_signals(signals):
    """عرض الإشارات بشكل واضح"""
    
    st.markdown("## 🎯 Trading Signals")
    
    score = signals['score']
    
    # تحديد اللون
    if score >= 5:
        color = "🟢"
        bg_color = "#1a3a1a"
        border_color = "#00ff00"
        st.balloons()
    elif score >= 2:
        color = "🟡"
        bg_color = "#3a3a1a"
        border_color = "#ffd700"
    elif score <= -5:
        color = "🔴"
        bg_color = "#3a1a1a"
        border_color = "#ff0000"
        st.snow()
    elif score <= -2:
        color = "🟠"
        bg_color = "#3a2a1a"
        border_color = "#ff6b00"
    else:
        color = "⚪"
        bg_color = "#1a1a1a"
        border_color = "#888888"
    
    # عرض النتيجة
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background-color: {bg_color}; border-radius: 10px; border: 3px solid {border_color};">
            <h1 style="color: white;">{color} Signal Score: {score}</h1>
            <p style="color: #aaa;">
                Strong BUY: ≥ 5 | BUY: 2-4 | NEUTRAL: -1 to 1 | SELL: -2 to -4 | Strong SELL: ≤ -5
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # عرض الإشارات
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🟢 BUY Signals")
        if signals['buy']:
            for signal in signals['buy']:
                st.success(f"✅ {signal}")
        else:
            st.info("ℹ️ No buy signals")
        
        if signals['strong_buy']:
            st.markdown("### 🔥 Strong BUY")
            for signal in signals['strong_buy']:
                st.success(f"🔥 {signal}")
    
    with col2:
        st.markdown("### 🔴 SELL Signals")
        if signals['sell']:
            for signal in signals['sell']:
                st.error(f"❌ {signal}")
        else:
            st.info("ℹ️ No sell signals")
        
        if signals['strong_sell']:
            st.markdown("### 🔥 Strong SELL")
            for signal in signals['strong_sell']:
                st.error(f"🔥 {signal}")
    
    # عرض الأسباب
    if signals['reasons']:
        st.markdown("### 📋 Signal Details")
        for reason in signals['reasons']:
            if '🟢' in reason:
                st.success(f"✅ {reason}")
            elif '🔴' in reason:
                st.error(f"❌ {reason}")
            else:
                st.info(f"ℹ️ {reason}")

# ====================== الشارت ======================
def create_chart(df):
    """إنشاء الشارت"""
    
    if df.empty:
        return go.Figure()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            '📈 Price Chart',
            '📊 Order Book',
            '📉 Volume',
            '📊 RSI & MACD'
        )
    )
    
    # Price
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#00ff00',
            decreasing_line_color='#ff0000'
        ),
        row=1, col=1
    )
    
    # SMA
    if 'SMA_20' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['SMA_20'], mode='lines', name='SMA 20', line=dict(color='#FFD700')),
            row=1, col=1
        )
    if 'SMA_50' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['SMA_50'], mode='lines', name='SMA 50', line=dict(color='#FF6B6B')),
            row=1, col=1
        )
    
    # Volume
    colors = ['#00ff00' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff0000' for i in range(len(df))]
    fig.add_trace(
        go.Bar(x=df['timestamp'], y=df['volume'], name='Volume', marker_color=colors),
        row=2, col=1
    )
    
    # RSI
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['RSI'], mode='lines', name='RSI', line=dict(color='#FF6B6B')),
            row=2, col=2
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=2)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=2)
    
    # MACD
    if 'MACD' in df.columns and 'Signal' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['MACD'], mode='lines', name='MACD', line=dict(color='#FFD700')),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(x=df['timestamp'], y=df['Signal'], mode='lines', name='Signal', line=dict(color='#FF6B6B')),
            row=1, col=2
        )
    
    fig.update_layout(
        height=800,
        template='plotly_dark',
        title_text='📊 XAUUSDT Trading Dashboard',
        showlegend=True
    )
    
    return fig

# ====================== الواجهة الرئيسية ======================
def main():
    st.title("🏆 Gold Trading Bot - Signals")
    st.markdown("### 🔥 Live XAUUSDT with Trading Signals")
    st.markdown("---")
    
    # ===== الشريط الجانبي =====
    with st.sidebar:
        st.header("⚙️ Settings")
        
        timeframe = st.selectbox(
            "⏱️ Timeframe",
            ["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
            index=0
        )
        
        candle_limit = st.slider(
            "📊 Number of Candles",
            min_value=50,
            max_value=500,
            value=200,
            step=50
        )
        
        st.divider()
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=True)
        
        st.divider()
        st.info("📡 Connected to Binance Futures")
        st.caption(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # ===== تحميل البيانات =====
    with st.spinner("🔄 Loading data..."):
        try:
            # جلب البيانات
            df = get_klines("XAUUSDT", timeframe, candle_limit)
            
            if df.empty:
                st.warning("⚠️ Using simulated data (API unavailable)")
                df = generate_mock_data(candle_limit)
            
            # حساب المؤشرات
            df = calculate_indicators(df)
            
            # توليد الإشارات
            signals = generate_trading_signals(df)
            
            # جلب الأوردر بوك
            bids, asks = get_order_book("XAUUSDT", 50)
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            return
    
    # ===== عرض الإشارات =====
    display_signals(signals)
    
    st.divider()
    
    # ===== عرض الشارت =====
    st.subheader("📈 Live Chart")
    fig = create_chart(df)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ===== عرض الأوردر بوك =====
    if not bids.empty and not asks.empty:
        st.subheader("📊 Order Book")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Bids")
            st.dataframe(bids.head(20), use_container_width=True)
        
        with col2:
            st.markdown("### 🔴 Asks")
            st.dataframe(asks.head(20), use_container_width=True)
    
    # ===== تحديث تلقائي =====
    if auto_refresh:
        st.caption("🔄 Auto-refreshing every 15 seconds...")
        time.sleep(15)
        st.rerun()

if __name__ == "__main__":
    main()
