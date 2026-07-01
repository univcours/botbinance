import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime
import numpy as np

# ====================== إعدادات الصفحة ======================
st.set_page_config(
    page_title="Gold Trading Bot - Signals",
    page_icon="📊",
    layout="wide"
)

# ====================== دوال جلب البيانات ======================
@st.cache_data(ttl=10)
def get_klines(symbol="XAUUSDT", interval="1m", limit=200):
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v1/klines"
    
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    
    try:
        response = requests.get(base_url + endpoint, params=params, timeout=10)
        if response.status_code != 200:
            return pd.DataFrame()
            
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
        return pd.DataFrame()

@st.cache_data(ttl=5)
def get_order_book(symbol="XAUUSDT", limit=50):
    base_url = "https://fapi.binance.com"
    endpoint = "/fapi/v1/depth"
    
    params = {
        "symbol": symbol,
        "limit": limit
    }
    
    try:
        response = requests.get(base_url + endpoint, params=params, timeout=10)
        if response.status_code != 200:
            return pd.DataFrame(), pd.DataFrame()
            
        data = response.json()
        
        if not data or 'bids' not in data or 'asks' not in data:
            return pd.DataFrame(), pd.DataFrame()
        
        bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
        asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
        
        return bids, asks
    
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame()

# ====================== المؤشرات والإشارات ======================
def calculate_indicators(df):
    """حساب المؤشرات الفنية"""
    
    # المتوسطات المتحركة
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
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
    
    if len(df) < 50:
        return {
            'buy': [],
            'sell': [],
            'strong_buy': [],
            'strong_sell': [],
            'neutral': ['⚠️ Not enough data'],
            'score': 0,
            'reasons': ['⚠️ Need more data for signals']
        }
    
    df = calculate_indicators(df)
    
    signals = {
        'buy': [],
        'sell': [],
        'strong_buy': [],
        'strong_sell': [],
        'neutral': [],
        'score': 0,
        'reasons': []
    }
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    score = 0
    
    # ===== 1. RSI =====
    if not pd.isna(last['RSI']):
        if last['RSI'] < 30:
            score += 2
            signals['buy'].append(f"RSI Oversold: {last['RSI']:.2f}")
            signals['reasons'].append(f"🟢 RSI oversold at {last['RSI']:.2f}")
        elif last['RSI'] > 70:
            score -= 2
            signals['sell'].append(f"RSI Overbought: {last['RSI']:.2f}")
            signals['reasons'].append(f"🔴 RSI overbought at {last['RSI']:.2f}")
    
    # ===== 2. MACD =====
    if not pd.isna(last['MACD']) and not pd.isna(last['Signal']):
        if last['MACD'] > last['Signal']:
            score += 1
            signals['buy'].append("MACD Bullish")
            signals['reasons'].append("🟢 MACD above signal line")
        else:
            score -= 1
            signals['sell'].append("MACD Bearish")
            signals['reasons'].append("🔴 MACD below signal line")
    
    # ===== 3. Bollinger Bands =====
    if not pd.isna(last['Lower_Band']) and not pd.isna(last['Upper_Band']):
        if last['close'] < last['Lower_Band']:
            score += 2
            signals['buy'].append("Price below Lower Band")
            signals['reasons'].append("🟢 Price below lower Bollinger Band (oversold)")
        elif last['close'] > last['Upper_Band']:
            score -= 2
            signals['sell'].append("Price above Upper Band")
            signals['reasons'].append("🔴 Price above upper Bollinger Band (overbought)")
    
    # ===== 4. المتوسطات المتحركة =====
    if not pd.isna(last['SMA_20']) and not pd.isna(last['SMA_50']):
        if last['SMA_20'] > last['SMA_50']:
            score += 1
            signals['buy'].append("SMA 20 > SMA 50 (Bullish)")
            signals['reasons'].append("🟢 SMA 20 above SMA 50 (uptrend)")
        else:
            score -= 1
            signals['sell'].append("SMA 20 < SMA 50 (Bearish)")
            signals['reasons'].append("🔴 SMA 20 below SMA 50 (downtrend)")
    
    # ===== 5. السعر مقابل المتوسطات =====
    if not pd.isna(last['SMA_20']):
        if last['close'] > last['SMA_20']:
            score += 1
            signals['buy'].append("Price above SMA 20")
        elif last['close'] < last['SMA_20']:
            score -= 1
            signals['sell'].append("Price below SMA 20")
    
    # ===== تحديد قوة الإشارة =====
    signals['score'] = score
    
    if score >= 5:
        signals['strong_buy'].append(f"🔥 STRONG BUY (Score: {score})")
        signals['buy'].append(f"Strong BUY signal")
    elif score >= 2:
        signals['buy'].append(f"📈 BUY (Score: {score})")
    elif score <= -5:
        signals['strong_sell'].append(f"🔥 STRONG SELL (Score: {score})")
        signals['sell'].append(f"Strong SELL signal")
    elif score <= -2:
        signals['sell'].append(f"📉 SELL (Score: {score})")
    else:
        signals['neutral'].append(f"⏸️ NEUTRAL (Score: {score})")
        signals['reasons'].append("⚪ No clear trend, wait for confirmation")
    
    return signals

# ====================== عرض الإشارات ======================
def display_signals(signals):
    """عرض الإشارات بشكل واضح"""
    
    st.markdown("## 🎯 Trading Signals")
    
    # ===== عرض النتيجة =====
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
    
    # ===== عرض الإشارات =====
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
    
    # ===== عرض الأسباب =====
    if signals['reasons']:
        st.markdown("### 📋 Signal Details")
        for reason in signals['reasons']:
            if '🟢' in reason:
                st.success(f"✅ {reason}")
            elif '🔴' in reason:
                st.error(f"❌ {reason}")
            else:
                st.info(f"ℹ️ {reason}")
    
    # ===== عرض المؤشرات الحالية =====
    st.markdown("### 📊 Current Indicators")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # نستخدم df من الـ session state
    if 'df' in st.session_state and not st.session_state.df.empty:
        df = st.session_state.df
        last = df.iloc[-1]
        
        with col1:
            if 'RSI' in last and not pd.isna(last['RSI']):
                st.metric("RSI", f"{last['RSI']:.2f}")
            else:
                st.metric("RSI", "N/A")
        with col2:
            if 'MACD' in last and not pd.isna(last['MACD']):
                st.metric("MACD", f"{last['MACD']:.4f}")
            else:
                st.metric("MACD", "N/A")
        with col3:
            if 'SMA_20' in last and not pd.isna(last['SMA_20']):
                st.metric("SMA 20", f"${last['SMA_20']:.2f}")
            else:
                st.metric("SMA 20", "N/A")
        with col4:
            if 'SMA_50' in last and not pd.isna(last['SMA_50']):
                st.metric("SMA 50", f"${last['SMA_50']:.2f}")
            else:
                st.metric("SMA 50", "N/A")
        with col5:
            if 'Upper_Band' in last and not pd.isna(last['Upper_Band']):
                st.metric("Upper Band", f"${last['Upper_Band']:.2f}")
            else:
                st.metric("Upper Band", "N/A")
    else:
        st.info("ℹ️ Waiting for data...")

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
            '📊 Indicators'
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
        
        depth_levels = st.slider(
            "📋 Order Book Depth",
            min_value=10,
            max_value=100,
            value=50,
            step=10
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
                st.error("❌ Failed to fetch data")
                return
            
            # حفظ في session state
            st.session_state.df = df
            
            # حساب المؤشرات
            df = calculate_indicators(df)
            
            # توليد الإشارات
            signals = generate_trading_signals(df)
            
            # جلب الأوردر بوك
            bids, asks = get_order_book("XAUUSDT", depth_levels)
            
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
        st.caption("🔄 Auto-refreshing every 10 seconds...")
        time.sleep(10)
        st.rerun()

if __name__ == "__main__":
    main()
