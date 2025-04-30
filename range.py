import pandas as pd
import MetaTrader5 as mt5
import trading_bot as bot

def is_range_visual( window=10, threshold_percent=1.0, max_body_ratio=0.3):
    """
    تشخیص بازار رنج با بررسی نوسان محدود و بدنه‌های کوچک کندل‌ها.
    
    پارامترها:
    - df: دیتافریم با ستون‌های ['open', 'high', 'low', 'close']
    - window: تعداد کندل اخیر برای بررسی (پیش‌فرض ۱۰)
    - threshold_percent: بیشترین نوسان مجاز بین High و Low (بر حسب درصد)
    - max_body_ratio: بیشینه نسبت بدنه کندل به طول آن (برای رد کردن کندل‌های قدرتی)

    خروجی:
    - True اگر بازار رنج باشد، False در غیر اینصورت
    """


    df,ask,bid=bot.FvgDetectorApp.get_data("EURUSD","1m",100) # گرفتن داده‌ها از متاتریدر 5
    if len(df) < window:
        return False  # دیتای کافی نیست

    recent = df[-window:].copy()

    # محاسبه High و Low کلی در بازه
    highest = recent['high'].max()
    lowest = recent['low'].min()
    avg_price = recent['close'].mean()

    # درصد نوسان
    range_percent = ((highest - lowest) / avg_price) * 100

    if range_percent > threshold_percent:
        return False  # نوسان زیاد است → بازار ترندی است

    # محاسبه بدنه کندل و نسبت آن به طول کل کندل
    recent['body'] = (recent['close'] - recent['open']).abs()
    recent['total_length'] = (recent['high'] - recent['low']).replace(0, 0.00001)
    recent['body_ratio'] = recent['body'] / recent['total_length']

    # بررسی تعداد کندل‌هایی که بدنه بزرگی دارند (کندل‌های قدرتی)
    strong_candles = recent[recent['body_ratio'] > max_body_ratio]

    if len(strong_candles) > 2:  # بیشتر از ۲ کندل قوی؟
        return False

    return True




if is_range_visual(window=10, threshold_percent=1.0, max_body_ratio=0.3):
    print("trend is range")
else:
    print("trend is not range")

def convert_timeframe(self, timeframe):
        timeframes = {
            "1m": mt5.TIMEFRAME_M1, "5m": mt5.TIMEFRAME_M5, "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30, "1h": mt5.TIMEFRAME_H1, "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1, "1w": mt5.TIMEFRAME_W1, "1mn": mt5.TIMEFRAME_MN1
        }
        return timeframes.get(timeframe)
def get_data(self, symbol, timeframe, num_bars=4):
        
        tf = self.convert_timeframe(timeframe)
        if tf is None:
            return None, None, None

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_bars)
        if rates is None:
            return None, None, None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        tick_info = mt5.symbol_info_tick(symbol)
        self.bid_price = tick_info.bid if tick_info else None
        self.ask_price = tick_info.ask if tick_info else None
        return df[['open', 'high', 'low', 'close']]

