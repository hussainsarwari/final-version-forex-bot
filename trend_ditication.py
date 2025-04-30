import requests
import pandas as pd
# import ccxt
import numpy as np
import time
import tkinter as tk





# # 🔑 وارد کردن API Key
# api_key = "rkwH95QU5XohCkQjYdnsD4SzyVidG5eTtLinL17LREmXfGWmuRctMn8Nkaez4eW9"
# api_secret = "BNE99Qwg0HtJX56Gm9rHMKvFJKwcyz0fvXg65g4E7azU5jPZ9ylN2dpCXMAjyWTw"

# exchange = ccxt.binance({
#     'apiKey': api_key,
#     'secret': api_secret,
#     'enableRateLimit': True
# })



import MetaTrader5 as mt5
import pandas as pd

def get_forex_ohlcv(symbol, timeframe, limit=100):
    # اتصال به متاتریدر 5
    if not mt5.initialize():
        raise ConnectionError("متاتریدر 5 راه‌اندازی نشد. لطفاً بررسی کنید که MT5 در حال اجرا است.")

    # تعریف تایم‌فریم‌ها
    timeframes = {
        "1m": mt5.TIMEFRAME_M1,
        "5m": mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "30m": mt5.TIMEFRAME_M30,
        "1h": mt5.TIMEFRAME_H1,
        "4H": mt5.TIMEFRAME_H4,
        "1D": mt5.TIMEFRAME_D1
    }

    if timeframe not in timeframes:
        raise ValueError("تایم‌فریم نامعتبر است. از بین این موارد انتخاب کنید: " + ", ".join(timeframes.keys()))

    # دریافت داده‌های OHLCV
    rates = mt5.copy_rates_from_pos(symbol, timeframes[timeframe], 0, limit)
    
    if rates is None:
        raise ValueError("عدم دریافت داده. لطفاً بررسی کنید که نماد صحیح است.")

    # تبدیل داده‌ها به DataFrame
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index("time", inplace=True)

    return df[["open", "high", "low", "close", "tick_volume"]]






# moving avarage 

# تابعی برای تشخیص روند بازار
def detect_trend(symbol, interval):
    limit=1000
    df = get_forex_ohlcv(symbol, interval, limit)
    
    # محاسبه میانگین متحرک کوتاه‌مدت (SMA) و بلند‌مدت (SMA)
    df['SMA_short'] = df['close'].rolling(window=20).mean()  # میانگین متحرک 20 کندل
    df['SMA_long'] = df['close'].rolling(window=50).mean()  # میانگین متحرک 50 کندل
    
    # تشخیص روند بر اساس مقایسه میانگین‌های متحرک
    if df['SMA_short'].iloc[-1] > df['SMA_long'].iloc[-1]:
        return "Uptrend"
    elif df['SMA_short'].iloc[-1] < df['SMA_long'].iloc[-1]:
        return "Downtrend"
    else:
        return "Sideways"


# RSI
def calculate_rsi(ohlcv_data, period=14):
    delta = ohlcv_data['close'].diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def rsi(symbol, timeframe):
    ohlcv = get_forex_ohlcv(symbol, timeframe=timeframe, limit=1000)
    ohlcv_data = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    ohlcv_data['timestamp'] = pd.to_datetime(ohlcv_data['timestamp'], unit='ms')

    # محاسبه RSI
    ohlcv_data['rsi'] = calculate_rsi(ohlcv_data)

    for i in range(1, len(ohlcv_data)):
        rsi_now = ohlcv_data['rsi'].iloc[i]

        # سیگنال خرید (RSI از پایین به بالا 30 را شکسته و کندل برگشتی زده)
        if  rsi_now < 33:
               return "oversold"

        # سیگنال فروش (RSI از بالا به پایین 70 را شکسته و کندل برگشتی زده)
        elif  rsi_now > 73:
              return "overbought"
        

    return 0  # اگر سیگنالی نبود



