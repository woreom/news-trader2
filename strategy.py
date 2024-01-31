## Import Libraries
from typing import Dict, List
from time import sleep
import threading

import numpy as np 
import pandas as pd        
import MetaTrader5 as mt5

from utils import log, try_on_internet, log_it
from get_data import get_candle, get_bid, get_ask, get_open_positions, get_data_from_mt5
from news_trading import calc_position_size, get_tick_size

# symbol = "XAUUSD"
# price = get_bid(initialize, symbol=symbol)
# request = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol,"volume": 0.01, "type": mt5.ORDER_TYPE_BUY, "price": price, 'sl': price-2, 'tp': price+2}
# trade = mt5.order_send(request)
# 187474302

@try_on_internet(counter_limit=40)
def open_position(request: Dict):
 
    trade = mt5.order_send(request)
    success = trade.order != 0
    return success, trade

@try_on_internet(counter_limit=40)
def modify_position(request: Dict):
    trade = mt5.order_send(request)
    success = trade[0] == 10009
    return success, trade

def set_action(initialize: List, positions: List, position_index: int, symbol: str, price_news_time: float):
    # get the current candle
    candle = get_candle(initialize=initialize, symbol=symbol, timeframe='1m')
    # initially consider our action as Cancel
    action = "Cancel"

    # Find if the first position is a buy, sell or cancel
    if (price_news_time < candle["Low"]):
        if positions[position_index]['Action'] == 'Sell':
            action = 'Sell'

    elif (price_news_time > candle["High"]):
        if positions[position_index]['Action'] == 'Buy':
            action = 'Buy'

    log(f'action: {action} price_news_time: {price_news_time} candle_low: {candle["Low"]} candle_high: {candle["High"]}')

    # Find if the second position is a buy, sell or cancel  
    if action == "Cancel":
        sleep(positions[1-position_index]["PendingTime"] - positions[position_index]["PendingTime"])
        log(f'The second sleep duraction for {positions[position_index]["Currency"]} was passed ({positions[1-position_index]["PendingTime"] - positions[position_index]["PendingTime"]} seconds) news:{positions[position_index]["News"]}')
        # update current candle
        candle = get_candle(initialize=initialize, symbol=symbol, timeframe='1m')
        if (price_news_time < candle["Low"]):
            action = 'Sell'
        elif (price_news_time > candle["High"]):
            action = 'Buy'
        log(f'action: {action} low: {candle["Low"]} high: {candle["High"]}')
    # Add Check if action contradicts our open positions
    open_positions = get_open_positions(initialize)
    num_buy = len(open_positions.loc[(open_positions['symbol'] == symbol) & (open_positions["action"] == "Buy")])
    num_sell = len(open_positions.loc[(open_positions['symbol'] == symbol) & (open_positions["action"] == "Sell")])
    

    if (action == "Buy" and num_sell > 0) or (action == "Sell" and num_buy > 0):
        log(f'action: {action} num_sell: {num_sell} num_buy: {num_buy}')
        action = "Cancel"

    return action

def count_num_hits(price, df):
    return df.gt(price).cumsum().where(df.le(price)).nunique() + df.le(price).cumsum().where(df.gt(price)).nunique() - 1

def PositionSize(symbol, entry, sl, risk):
    """
     Calculate the position size based on the given trade parameters.
    
    Parameters:
    symbol: A string representing the currency symbol for which to calculate the position size.
    entry: A float representing the trade entry price.
    sl: A float representing the trade stop loss price.
    risk: A float representing the maximum amount of capital to risk in the account's base currency.
    
    Returns:
    A float representing the position size in lots.
    
    The function first selects the given symbol using `mt5.symbol_select()`,
    and retrieves the trade tick size and value information using `mt5.symbol_info()`.
    The function then retrieves the current tick information for the symbol using `mt5.symbol_info_tick()`,
    and calculates the minimum allowed distance as 5 times the tick size. 
    The function then calculates the number of ticks at risk based on the entry price and stop loss price,
    and calculates the position size in lots based on the maximum amount of capital to risk in the account's base currency.
    
    the function returns the calculated position size in lots as a float, rounded to two decimal places.
    
    Examples:
    # Calculate the position size for a trade with EURUSD
    symbol = 'EURUSD'
    entry = 1.2345
    sl = 1.2300
    risk = 1000  # Maximum amount of capital to risk is $1000
    position_size = PositionSize(symbol, entry, sl, risk)
     """
     
     
    mt5.symbol_select(symbol, True)
    symbol_info = mt5.symbol_info(symbol)
    

    tick_size = symbol_info.trade_tick_size
    tick_value = symbol_info.trade_tick_value
    
    pips_at_risk  = np.abs(entry - sl) / tick_size

    
    lot = risk / (pips_at_risk * tick_value)
    
    if symbol=='XAUUSD': lot/=10 
    
    if lot < symbol_info.volume_min : lot=symbol_info.volume_min
    elif lot > symbol_info.volume_max : lot=symbol_info.volume_max

    return np.round(lot, 2)



def Open_Position(trade_info):
    """
    This function takes a dictionary with trade information,
    including the entry point, take profit, step loss, position size, currency name and action
    (buy or sell), and creates a market order or a pending order to open a position
    in the specified financial instrument.
    
    Args:
    trade_info (dict): A dictionary containing trade information, including the
    entry point, take profit, step loss, position size,currency name and action (buy or sell).
    
    Returns:
    dict: A dictionary containing information about the trade order, including the
    order ticket number, trade operation (buy or sell), and trade result (successful
    or unsuccessful).
    """
    # Retrieve the number of digits for the currency pair being traded
    print(trade_info[0]['PendingTime'])
    position_index = np.argmin((trade_info[0]['PendingTime'], trade_info[1]['PendingTime']))
    print(position_index)
    time_info = trade_info[position_index]['PendingTime']
    sleep(time_info)

    symbol=trade_info[position_index]['Currency']
    digit = mt5.symbol_info(symbol).digits
    price_news_time = trade_info[position_index]['price_news_time']
    initialize= ["51834380", "4wsirwes", "Alpari-MT5-Demo"]
    for _ in range(3):
        df =get_data_from_mt5(initialize=initialize, Ticker=symbol, TimeFrame='1m')

    action = None
    if (price_news_time < df.iloc[-1]["Low"]):
        if trade_info[position_index]['Action'] == 'Sell':
            action = 'Sell'
    elif (price_news_time > df.iloc[-1]["High"]):
        if trade_info[position_index]['Action'] == 'Buy':
            action = 'Buy'
    if action == None:
        sleep(trade_info[1-position_index]["PendingTime"] - trade_info[position_index]["PendingTime"]) 
        for _ in range(3):
            df =get_data_from_mt5(initialize=initialize, Ticker=symbol, TimeFrame='1m')
        if (price_news_time < df.iloc[-1]["Low"]):
            action = 'Sell'
        elif (price_news_time > df.iloc[-1]["High"]):
            action = 'Buy'

    if action == 'Sell':
        position_info = trade_info[1]
        price = mt5.symbol_info_tick(symbol).ask

    elif action == 'Buy':
        position_info = trade_info[0]
        price = mt5.symbol_info_tick(symbol).bid
      
    else:
        print('position failed')
        return
    log(f'position info: {position_info}')   
    log(f'position info: {price}')  
        # action = 'Buy'
        # position_info = trade_info[0]
        # price = mt5.symbol_info_tick(symbol).bid
    print(action)    
    print(position_info)
    order_type = {'Buy': mt5.ORDER_TYPE_BUY, 'Sell': mt5.ORDER_TYPE_SELL}
    tp = np.round(position_info['TakeProfit'], digit)
    sl = np.round(position_info['StepLoss'], digit)
    lot = np.double(position_info['PositionSize'])        
    request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": lot,
    "type": order_type[action],
    "price": price,
    "sl": sl,  
    "tp": tp,
    #"type_filling":mt5.ORDER_FILLING_RETURN,
    "comment": f"{position_info['News'][:3]},{position_info['TimeFrame']},{round(position_info['WinRate']*100, ndigits=2)}",
    }
    
    # Send the pending order to the trading server
    counter = 0
    class dummy():
        order=0
    trade= dummy()

    if np.abs((request["tp"] - request["price"]) / (request['sl'] - request['price'])) <=0.2:
        return
    
    while trade.order == 0 and counter<=40:
        trade = mt5.order_send(request)
        print(trade)
        #print trade retcode
        # if trade.retcode != mt5.TRADE_RETCODE_DONE:
        #     print("2. order_send failed, retcode={}".format(trade.retcode))
        sleep(1)
        counter+=1
    log(f'opend position: {trade.order}')
    # Return information about the trade order
    sleep(trade_info[[position_index]]['TimeFrame']*60*60 - trade_info[position_index]['PendingTime'])
    risk_free_request = {
    "action": mt5.TRADE_ACTION_SLTP,
    "symbol": symbol,    
    "sl": price,  
    "tp": tp,
    "position": trade.order, 
    #"type_filling":mt5.ORDER_FILLING_RETURN,
    # "comment": f"{position_info['News'][:3]},{position_info['TimeFrame']},{round(position_info['WinRate']*100, ndigits=2)}",
    }
    risk_free_trade =[0]
    while risk_free_trade[0] != 10009:
        trade = mt5.order_send(risk_free_request)
        print(trade)

    return trade, request


def Close_Position(trade_order, symbol, sleep_time):
    """
    Close or remove a position in MetaTrader 5.
    
    trade_order: int, the ticket number of the trade to close or remove
    request: dict, the trade request object returned by mt5.orders_get() for the trade
    action: str, 'Close' to close the trade or 'Remove' to remove the trade
    symbol: str, the symbol of the currency pair for the trade
    sleep_time: int, the number of seconds to wait before executing the trade action
    
    """

    sleep(sleep_time)
    counter = 0
    result = False
    while not result and counter<=40:
        result=mt5.Close(symbol=symbol,ticket=int(trade_order))
        result=mt5.order_send({"order": trade_order, "action": mt5.TRADE_ACTION_REMOVE})
        sleep(10)
        counter+=1

    log(f'closed position: {trade_order}')
    return result

def Control_Position(initialize, trade_info):
    
    """
    Control the lifecycle of a position in MetaTrader 5.
    
    initialize: list, contains login, password, and server information to connect to the MT5 terminal
    trade_info: dict, contains information for the trade to open, including currency pair, trade direction, 
    lot size, stop loss, and take profit
    max_pending_time: int, the maximum time in seconds to wait for a pending order to execute
    max_open_time: int, the maximum time in seconds to keep an open trade before closing it

    """
    # Initialization
    mt5.initialize()
    mt5.login(login=initialize[0],password=initialize[1],server=initialize[2])
    
    #Open_Position(trade_info)
    #print(trade_info)
    t1 = threading.Thread(target=Open_Position, args=[trade_info])
    t1.start()
    #t1 = threading.Thread(target=Close_Position, args=(trade.order, trade_info['Currency'], max_open_time))
    #t1.start()
    # return trade.order



def Control_Positions(initialize, positions, tracker, timezone):
    # Set obvious arguments
    now = pd.Timestamp('today', tzinfo=timezone).replace(tzinfo=None)
    symbol=positions[0]['Currency']
    digit = mt5.symbol_info(symbol).digits
    order_type = {'Buy': mt5.ORDER_TYPE_BUY, 'Sell': mt5.ORDER_TYPE_SELL, 'Cancel': None}
    position_order = {'Buy': 0, 'Sell': 1}

    # Wait until one of the positions needs to be open
    position_index = np.argmin((positions[0]['PendingTime'], positions[1]['PendingTime']))
    time_info = positions[position_index]['PendingTime']
    # get the price in time of news
    price_news_time = positions[position_index]['price_news_time']
    sleep(time_info)
    log(f'The first sleep duration for {positions[position_index]["Currency"]} was passed ({time_info} seconds) news:{positions[position_index]["News"]}')
    # Wait until action is set to 'Buy', 'Sell' or 'Cancel'
    action = set_action(initialize, positions, position_index, symbol, price_news_time)
    price = get_ask(initialize, symbol) if action == 'Sell' else get_bid(initialize, symbol)
    ask = get_ask(initialize, symbol)
    bid = get_bid(initialize, symbol)
    spread = abs(ask - bid)
    multiplier = get_tick_size(symbol)
    # Modify position to be risk-free
    if (bid < price+spread < ask) or (bid < price-spread < ask):
        correct_price_bid = np.round(bid - 2*multiplier, digit)
        correct_price_ask = np.round(ask + 2*multiplier, digit)
    else:
        correct_price_bid =  np.round(price-spread, digit)
        correct_price_ask = np.round(price+spread, digit)   
    # Set our trading info
    position_info = positions[1] if action == 'Sell' else positions[0]
    price = correct_price_ask if action == 'Sell' else correct_price_bid
    log(f'price: {price}')

    
    tp = np.round(position_info['TakeProfit'], digit)
    sl = np.round(position_info['StepLoss'], digit)
    #lot = np.double(position_info['PositionSize'])
    
    
    sl_gap = np.abs(sl - price)
    tp_gap = np.abs(tp - price)
    final_ratio = 1.15

    if tp_gap / sl_gap > 1:
        tp = np.round(price + sl_gap, digit) if action == "Buy" else np.round(price - sl_gap, digit) if action == "Sell" else tp
    elif tp_gap / sl_gap < 1:
        sl = np.round(price - tp_gap, digit) if action == "Buy" else np.round(price + tp_gap, digit) if action == "Sell" else sl

    # dif_sl = np.abs(price - sl)
    dif_tp = np.abs(price - tp)
    dif_sl = (dif_tp / final_ratio)
    sl = np.round(price - dif_sl, digit) if action == "Buy" else np.round(price + dif_sl, digit) if action == "Sell" else sl


    


    # if tp_gap / sl_gap > ratio:
    #     tp = np.round(price + sl_gap * ratio, digit) if action == "Buy" else np.round(price - sl_gap * ratio, digit) if action == "Sell" else tp
    # elif tp_gap / sl_gap < ratio:
    #     sl = np.round(price - tp_gap / ratio, digit) if action == "Buy" else np.round(price + tp_gap / ratio, digit) if action == "Sell" else sl


    lot = np.double(calc_position_size(symbol, price, sl, position_info['Risk']))
    if symbol == "GBPJPY":
        lot = np.double(lot/2)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type[action],
        "price": price,
        "sl": np.round(sl, digit),  
        "tp": np.round(tp, digit),
        #"type_filling":mt5.ORDER_FILLING_RETURN,
        "comment": f"{position_info['News'][:3]},{position_info['TimeFrame']},{round(position_info['WinRate']*100, ndigits=2)}",
    }
    
    # check if R/R is less than 0.2
    rr = np.abs((request["tp"] - request["price"]) / (request['sl'] - request['price']))
    tracker['rr'] = rr
    if rr <=0.2:
        action = 'Cancel'
        log(f'action canceled because R/R is less than 0.2')
        
    if lot > 7: action = 'Cancel'
    # Check if price_news_time has been hit more than space

    for key in request.keys():
        if key not in ['comment', 'type', 'action']:
            tracker[key]= request[key]
        tracker['action'] = action

    if action != 'Cancel':
        slept_time = (positions[position_index]['PendingTime'] if position_index == position_order[action] else positions[1-position_index]['PendingTime'])
        num_candles = int(np.round(slept_time/60, decimals = 0)/5)
        df = get_data_from_mt5(initialize=initialize, Ticker=symbol, TimeFrame='5m')
        # count = max([count_num_hits(price_news_time, df[column].iloc[-num_candles:]) for column in ['Open', 'High', 'Low', 'Close',]])
        # print(count)
        # if position_info["Space"] < count:
        #     log(f"Position {position_info} was canceled becasue Space:{position_info['Space']} < Count:{count} slept_time:{slept_time} num_candles:{num_candles}")
        #     action = 'Cancel'

    # Check if action is 'Cancel'
    if action == 'Cancel':
        print('cancel')
        with open(f'static/report_{now.strftime("%Y-%m-%d")}.txt', 'a') as f:
                f.write(f'{tracker}\n')
        return
    
    # Send the market order to the MT5
    now = pd.Timestamp('today', tzinfo=timezone).replace(tzinfo=None)
    tracker['open_time'] = now.strftime("%Y-%m-%d %H:%M:%S")
    flag, trade= open_position(request=request)
    tracker['ticket'] = trade.order
    # log information about the trade order
    log(f'opend position: {trade.order}' if flag else f'failed to open position: {position_info}')

    # wait to risk-free the position (close it)
    sleep(position_info['TimeFrame']*60*60 - slept_time)

    # Find our profit or loss
    open_positions = get_open_positions(initialize)
    try:
        is_profit = open_positions.loc[open_positions['ticket'] == trade.order]['profit'].iloc[0] > 0
    ## If trader.order does not match any tickets IndexError: single positional indexer is out-of-bounds
    except IndexError as e:
        if str(e) == "single positional indexer is out-of-bounds":
            with open(f'static/report_{now.strftime("%Y-%m-%d")}.txt', 'a') as f:
                f.write(f'{tracker}\n')
            return None, None
    except KeyError as e:
        if str(e) == "ticket":
            with open(f'static/report_{now.strftime("%Y-%m-%d")}.txt', 'a') as f:
                f.write(f'{tracker}\n')
            return None, None

    #get spread
    ask = get_ask(initialize, symbol)
    bid = get_bid(initialize, symbol)
    spread = abs(ask - bid)
    multiplier = get_tick_size(symbol)
    # Modify position to be risk-free
    if (bid < price+spread < ask) or (bid < price-spread < ask):
        correct_price_bid = np.round(bid - 2*multiplier, digit)
        correct_price_ask = np.round(ask + 2*multiplier, digit)
    else:
        correct_price_bid =  np.round(price-spread, digit)
        correct_price_ask = np.round(price+spread, digit)    

    if action == 'Buy':
        risk_free_request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,    
        "sl": price if is_profit else sl,  
        "tp": tp if is_profit else price,
        "position": trade.order, 
        }

    if action == 'Sell':
        risk_free_request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,    
            "sl": price if is_profit else sl,  
            "tp": tp if is_profit else price,
            "position": trade.order, 
            }

    # Send modification to MT5
    now = pd.Timestamp('today', tzinfo=timezone).replace(tzinfo=None)
    tracker['close_time'] = now.strftime("%Y-%m-%d %H:%M:%S")
    tracker['profit'] = open_positions.loc[open_positions['ticket'] == trade.order]['profit'].iloc[0]
    tracker['risk-free_price'] = ask if action == 'Buy' else bid
    tracker['risk-free_sl'] = risk_free_request['sl']
    tracker['risk-free_tp'] = risk_free_request['tp']
    tracker['risk-free_profit'] = None
    tracker['risk-free_close_time'] = None

    success, trade = modify_position(request= risk_free_request)
    log(f'{success}  {trade}')

    with open(f'static/report_{now.strftime("%Y-%m-%d")}.txt', 'a') as f:
        f.write(f'{tracker}\n')

    return trade, request
    
