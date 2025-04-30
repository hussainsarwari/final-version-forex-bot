import MetaTrader5 as mt5

order_id = 0


def initialize_mt5():
    if not mt5.initialize():
        print("Error: Can not connect to MetaTrader 5.")
        return False
    return True


def shutdown_mt5():
    mt5.shutdown()


def get_position():
    position = mt5.positions_get(ticket=order_id)
    if not position:
        print(f"Could not find the order with ID = {order_id}.")
        return None
    return position[0]


def get_symbol_info(symbol):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Cannot find information about {symbol}.")
    return symbol_info


def get_mid_candle(symbol, tm):
    initialize_mt5()
    mid_candle = mt5.copy_rates_from_pos(symbol, tm, 0, 4)

    return mid_candle[1][2], mid_candle[1][3]#high and low of the mid candle

def trailing_stop_loss(symbol, tm, trade_type):
    if not initialize_mt5():
        return False

    mid_candle_high,mid_candle_low = get_mid_candle(symbol, tm)

    position = mt5.positions_get()
  
    if len(position) == 0:
        return 0
    order_id=position[0][0]
 
    if position is None:
    
        return False
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
  
        return False

    current_price = mt5.symbol_info_tick(symbol).ask if trade_type == "buy" else mt5.symbol_info_tick(symbol).bid

    if trade_type == "buy":
        for position in position:
            if position.type == mt5.ORDER_TYPE_SELL:
               return "Stop loss not updated duo to the order buy but new fvg is sell."
           

        new_stop_loss = mid_candle_low - round((current_price - mt5.symbol_info_tick(symbol).bid),4)
        return update_stop_loss(symbol, new_stop_loss, order_id)

    elif trade_type == "sell":
        for position in position:
            if position.type == mt5.ORDER_TYPE_BUY:
               return "Stop loss not updated duo to the order sell but new fvg is buy."
        new_stop_loss = mid_candle_high + round((mt5.symbol_info_tick(symbol).ask - mt5.symbol_info_tick(symbol).bid),4)
        return update_stop_loss(symbol, new_stop_loss, order_id)


    return f"Stop loss not updated."


def update_stop_loss(symbol, new_stop_loss,order_id):
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": order_id,
        "sl": new_stop_loss,
        "magic": 123456,
        "comment": "Trailing Stop Update",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Could not update stop loss: {result.comment}")
    else:
        print(f"Stop loss updated successfully to {new_stop_loss}.")
    return f"Stop loss updated successfully to {new_stop_loss}"


def get_pip_value(symbol, lot_size, order_type):
    symbol_info = get_symbol_info(symbol)
    if not symbol_info:
        return None

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return None

    price = tick.ask if order_type == "buy" else tick.bid
    pip_value = (0.0001 * lot_size / price) * symbol_info.trade_contract_size

    return pip_value


def calculate_lot(risk, stop_loss_pips, symbol, order_type):
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    pip_value = get_pip_value(symbol, 0.01, order_type)
    if pip_value is None:
        return None

    spread_pips = get_spread_pips(symbol)
    total_pips = stop_loss_pips + spread_pips
    lot = risk / (total_pips * pip_value)
 
    return round(lot, 2)

def get_spread_pips(symbol):
    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None
    return symbol_info.spread


def open_trade(risk, trade_type, symbol, tm):

    global order_id
    if not initialize_mt5():
        return None

    symbol_info = get_symbol_info(symbol)
    if symbol_info is None:
        return None

    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None


    mid_candle_high, mid_candle_low = get_mid_candle(symbol, tm)

    ask_price = tick.ask
    bid_price = tick.bid
    spread = ask_price - bid_price
    if spread > 0.00015:
        print(f"Spread is too high: {spread}")
        return None   

    stop_loss_price = mid_candle_high + 0.00015 if trade_type == "sell" else mid_candle_low - 0.00015
    
    order_type = mt5.ORDER_TYPE_SELL if trade_type.lower() == "sell" else mt5.ORDER_TYPE_BUY
    price = bid_price if trade_type.lower() == "sell" else ask_price

    stop_loss_pips = abs(price - stop_loss_price) / symbol_info.point
    lot = calculate_lot(risk, stop_loss_pips, symbol, trade_type.lower())
    print(f"Spread: {lot}") 
  
    
    if lot == 0:
        return "error:256"

    order_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": stop_loss_price,
        "deviation": 2,
        "magic": 123456,
        "comment": f"Python {trade_type.capitalize()} Order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    order_result = mt5.order_send(order_request)
    if order_result.retcode < mt5.TRADE_RETCODE_DONE:
        print(f"Error executing order: {order_result.comment}")
    else:
        print(f"Order executed successfully with order id: {order_result.order}")
    
    order_id = order_result.order
    return order_request
