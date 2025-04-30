import tkinter as tk
from tkinter import messagebox, ttk
import MetaTrader5 as mt5
import pandas as pd
import requests
import trading_operation as trading_operation
import trend_ditication as trend
import pytz
import threading
import time
# Telegram settings
BOT_TOKEN = "7742820043:AAFTeg18SOxYiCgF4U39yR51VuXuvta8aPM"
CHAT_ID = "1983334321"

class FvgDetectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 FVG Detector - Smart Trading")
        self.root.geometry("900x650")
        self.root.config(bg="#2C3E50")

        self.is_trade_open = False
        self.running = False
        self.latest_fvg_low_high = {"low": None, "high": None}
        self.previous_fvg = {"bullish": None, "bearish": None}

        self.bid_price = 0
        self.ask_price = 0

        self.symbol_var = tk.StringVar()
        self.timeframe_var = tk.StringVar()
        self.risk_entry = None
        self.message_box = None
        self.result_label = None

        self.initialize_ui()

    def initialize_ui(self):
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 12, "bold"), padding=5)
        style.configure("TLabel", font=("Arial", 12), background="#2C3E50", foreground="white")
        style.configure("TEntry", font=("Arial", 12))

        title_label = ttk.Label(self.root, text="🚀 FVG Detector", font=("Arial", 18, "bold"))
        title_label.pack(pady=15)

        frame = tk.Frame(self.root, bg="#34495E", padx=10, pady=10, bd=2, relief=tk.GROOVE)
        frame.pack(pady=10, padx=20, fill=tk.X)

        symbol_label = ttk.Label(frame, text="Symbol:")
        symbol_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        symbol_options = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
        symbol_dropdown = ttk.Combobox(frame, textvariable=self.symbol_var, values=symbol_options)
        symbol_dropdown.grid(row=0, column=1, padx=5, pady=5)

        risk_label = ttk.Label(frame, text="Risk (Money):")
        risk_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.risk_entry = ttk.Entry(frame)
        self.risk_entry.grid(row=1, column=1, padx=5, pady=5)

        timeframe_label = ttk.Label(frame, text="Timeframe:")
        timeframe_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        timeframe_options = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        timeframe_dropdown = ttk.Combobox(frame, textvariable=self.timeframe_var, values=timeframe_options)
        timeframe_dropdown.grid(row=2, column=1, padx=5, pady=5)

        self.message_box = tk.Text(self.root, height=10, width=80)
        self.message_box.pack(pady=10)

        btn_frame = tk.Frame(self.root, bg="#2C3E50")
        btn_frame.pack(pady=10)

        start_button = ttk.Button(btn_frame, text="▶ Start", command=self.start_monitoring)
        start_button.grid(row=0, column=0, padx=10)

        stop_button = ttk.Button(btn_frame, text="⏹ Stop", command=self.stop_monitoring)
        stop_button.grid(row=0, column=1, padx=10)

        self.result_label = ttk.Label(self.root, text="Waiting for FVG detection...", font=("Arial", 12))
        self.result_label.pack(pady=10)

    def log_message(self, message):
        self.message_box.insert(tk.END, message + "\n")
        self.message_box.see(tk.END)

    def initialize_mt5(self):
        if not mt5.initialize():
            messagebox.showerror("Error", "MetaTrader 5 initialization failed.")
            return False
        return True

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
        return df[['open', 'high', 'low', 'close']], self.bid_price, self.ask_price

    def detect_fvg(self, df,symbol,timeframe):
        latest_fvg = {"bullish": None, "bearish": None}
        for i in range(3, len(df)):
            if df['close'].iloc[i-2] > df['open'].iloc[i-2] and df['low'].iloc[i-1] > df['high'].iloc[i-3] and trend.detect_trend(symbol,timeframe) == "Uptrend" and trend.rsi(symbol,timeframe) !='oversold':
                latest_fvg["bullish"] = (df.index[i-1], df['open'].iloc[i-1], df['close'].iloc[i-1])
            if df['close'].iloc[i-2] < df['open'].iloc[i-2] and df['high'].iloc[i-1] < df['low'].iloc[i-3] and trend.detect_trend(symbol,timeframe) == "Downtrend" and trend.rsi(symbol,timeframe) !='overbought':
               latest_fvg["bearish"] = (df.index[i-1], df['open'].iloc[i-1], df['close'].iloc[i-1])
        return latest_fvg

    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data)

    def check_fvg(self):
        if not self.running:
            return
        symbol = self.symbol_var.get()
        timeframe = self.timeframe_var.get()
        risk = self.risk_entry.get()
        risk= float(risk) 
        print(f"Risk: {risk}")
    

        df, bid_price, ask_price = self.get_data(symbol, timeframe)
        if df is None:
            message = f"Could not get data for {symbol} on {timeframe}. {df}: {bid_price} :{ask_price}"
            self.log_message(message)
            return

        latest_fvg = self.detect_fvg(df,symbol,timeframe)
        result_text = f" Checking {symbol} on {timeframe}...\n"
        self.log_message(result_text)

        # Bullish FVG detection and trade execution
        if latest_fvg["bullish"] != self.previous_fvg["bullish"]:
            self.send_telegram_message(f"New Bullish FVG detected: {latest_fvg['bullish']}")
            self.previous_fvg["bullish"] = latest_fvg["bullish"]
            self.execute_trade('buy', symbol, timeframe, risk)

        # Bearish FVG detection and trade execution
        elif latest_fvg["bearish"] != self.previous_fvg["bearish"]:
            self.send_telegram_message(f"New Bearish FVG detected: {latest_fvg['bearish']}")
            self.previous_fvg["bearish"] = latest_fvg["bearish"]
            self.execute_trade('sell', symbol, timeframe, risk)

    def execute_trade(self, trade_type, symbol, timeframe, risk):
        if self.is_trade_open:
            result_text = f"Trailing stop loss for {trade_type}"
            self.log_message(result_text)
            self.send_telegram_message(result_text)
            self.result_label.config(text=result_text)
            trading_operation.trailing_stop_loss(symbol, self.convert_timeframe(timeframe), trade_type)
        else:
            result = trading_operation.open_trade(risk, trade_type, symbol, self.convert_timeframe(timeframe))
            if result == 'error:256':
                result_text = f"lot size is too small."
                self.log_message(result_text)
                self.send_telegram_message(result_text)
            else:
                self.is_trade_open = True
                message = f"Order {trade_type} executed: {result}"
                self.send_telegram_message(message)
                result_text = f"Order {trade_type} executed successfully."
             

            self.log_message(result_text)
            self.result_label.config(text=result_text)

    def start_monitoring(self):
        if not self.running:
            mt5.initialize()
            self.running = True
            self.result_label.config(text="🚀 Searching for FVG...")
            self.log_message("Monitoring started...")
            thread = threading.Thread(target=self.monitor)
            thread.daemon = True
            thread.start()

    def monitor(self):
      
        while self.running:

            self.check_fvg()
            position = mt5.positions_get()
  
            if len(position) == 0:
                self.is_trade_open = False
           
            time.sleep(5) 
         

    def stop_monitoring(self):
        self.running = False
        self.result_label.config(text="❌ Monitoring Stopped.")
        self.log_message("Monitoring stopped.")
        mt5.shutdown()


def main():
    root = tk.Tk()
    app = FvgDetectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
