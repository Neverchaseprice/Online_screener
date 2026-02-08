import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def normalize_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    return df

def calculate_ema(series, period):
    """Расчет экспоненциальной скользящей средней"""
    return series.ewm(span=period, adjust=False).mean()

def calculate_rsi(series, period=14):
    """Расчет RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_trend_ema(df, fast_period=21, slow_period=55):
    """Определяет тренд на основе 21/55 EMA"""
    if len(df) < max(fast_period, slow_period) + 10:
        return None
    
    ema_fast = calculate_ema(df['Close'], fast_period)
    ema_slow = calculate_ema(df['Close'], slow_period)
    
    if len(ema_fast) == 0 or len(ema_slow) == 0:
        return None
    
    last_fast = ema_fast.iloc[-1]
    last_slow = ema_slow.iloc[-1]
    
    if last_fast > last_slow:
        return "bullish"
    elif last_fast < last_slow:
        return "bearish"
    else:
        return "neutral"

def get_price_vs_ema(df, period=200):
    """Определяет, выше или ниже цена относительно EMA"""
    if len(df) < period + 10:
        return None
    
    ema = calculate_ema(df['Close'], period)
    
    if len(ema) == 0:
        return None
    
    last_price = df['Close'].iloc[-1]
    last_ema = ema.iloc[-1]
    
    if last_price > last_ema:
        return "above"
    elif last_price < last_ema:
        return "below"
    else:
        return "equal"

def calculate_trend_strength(hourly_trend, daily_trend, weekly_trend):
    """Определяет силу тренда на основе совпадения на разных ТФ"""
    mid_term = None
    global_trend = None
    strength = None
    
    # MidTerm тренд: 4h и 1d совпадают
    if hourly_trend is not None and daily_trend is not None and hourly_trend == daily_trend:
        mid_term = hourly_trend
    
    # Global тренд: 1d и 1w совпадают
    if daily_trend is not None and weekly_trend is not None and daily_trend == weekly_trend:
        global_trend = daily_trend
    
    # STRONG: MidTerm и Global совпадают
    if mid_term is not None and global_trend is not None and mid_term == global_trend:
        strength = "STRONG"
    
    return mid_term, global_trend, strength

def analyze_asset_trends(name, ticker):
    """Анализирует тренды для одного актива на всех таймфреймах"""
    try:
        # Загрузка данных
        df_1h = normalize_df(yf.download(ticker, period="730d", interval="1h", progress=False))
        
        if len(df_1h) < 100:
            return None
        
        # Конвертация в МСК
        if df_1h.index.tz is None:
            df_1h.index = df_1h.index.tz_localize('UTC')
        df_1h.index = df_1h.index.tz_convert('Europe/Moscow')
        
        # Агрегация в 4h
        df_4h = df_1h.resample('4h').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        # Агрегация в 1d
        df_1d = df_1h.resample('D').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        # Агрегация в 1w
        df_1w = df_1h.resample('W').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        # Расчет трендов на основе 21/55 EMA
        trend_1h = get_trend_ema(df_1h, 21, 55)
        trend_4h = get_trend_ema(df_4h, 21, 55)
        trend_1d = get_trend_ema(df_1d, 21, 55)
        trend_1w = get_trend_ema(df_1w, 21, 55)
        
        # Расчет силы тренда
        mid_term, global_trend, strength = calculate_trend_strength(trend_4h, trend_1d, trend_1w)
        
        # RSI 14d
        rsi_14d = None
        if len(df_1d) >= 20:
            rsi_series = calculate_rsi(df_1d['Close'], 14)
            if len(rsi_series.dropna()) > 0:
                rsi_14d = rsi_series.iloc[-1]
        
        # Цена относительно 200 EMA на 4h
        price_vs_200ema_4h = get_price_vs_ema(df_4h, 200)
        
        return {
            'name': name,
            'ticker': ticker,
            'trend_1h': trend_1h,
            'trend_4h': trend_4h,
            'trend_1d': trend_1d,
            'trend_1w': trend_1w,
            'mid_term': mid_term,
            'global_trend': global_trend,
            'strength': strength,
            'rsi_14d': rsi_14d,
            'price_vs_200ema_4h': price_vs_200ema_4h
        }
        
    except Exception as e:
        print(f"Ошибка при анализе {name} ({ticker}): {str(e)}")
        return None

def generate_trend_dashboard(assets):
    """Генерирует дашборд трендов для списка активов"""
    dashboard_data = []
    
    for asset in assets:
        print(f"Анализ тренда: {asset['name']} ({asset['ticker']})...")
        trend_data = analyze_asset_trends(asset['name'], asset['ticker'])
        
        if trend_data is not None:
            dashboard_data.append(trend_data)
    
    return dashboard_data