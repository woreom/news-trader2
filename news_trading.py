import pytz
from datetime import datetime
from datetime import timedelta
from typing import List, Callable, Dict, Tuple
from time import sleep

import numpy as np
import pandas as pd
import MetaTrader5 as mt5


from get_data import get_price
from utils import log

__SHEET__NAME__={"USD":"United States", "JPY":"Japan", "EUR":"Euro Zone", "GER":"Germany", "GBP":"United Kingdom",
 "NZD":"New Zealand", "CAD":"Canada", "CHF":"Switzerland",}

__MULTIPLIER__VALUE__ = {
    'AUDJPY': 0.001, 'AUDUSD': 1e-05, 'AUDCAD': 1e-05, 'AUDCHF': 1e-05, 'CADCHF': 1e-05,
    'CADJPY': 0.001, 'CHFJPY': 0.001, 'GBPCHF': 1e-05, 'EURAUD': 1e-05, 'EURCAD': 1e-05,
    'EURGBP': 1e-05, 'EURJPY': 0.001, 'EURNZD': 1e-05, 'EURUSD': 1e-05, 'EURCHF': 1e-05,
    'GBPAUD': 1e-05, 'GBPJPY': 0.001, 'GBPUSD': 1e-05, 'GBPCAD': 1e-05, 'GBPNZD': 1e-05,
    'NZDCAD': 1e-05, 'NZDCHF': 1e-05, 'NZDJPY': 0.001, 'NZDUSD': 1e-05, 'USDCAD': 1e-05,
    'USDCHF': 1e-05, 'USDJPY': 0.001, 'XAUUSD': 0.01
    }


def get_tick_size(symbol: str) -> float:
    """
    Retrieves the tick size for a given symbol.

    Args:
        symbol (str): The symbol for which to retrieve the tick size.

    Returns:
        float: The tick size of the symbol.

    Raises:
        ValueError: If the symbol is not valid or not found.
    """
    mt5.symbol_select(symbol, True)
    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        raise ValueError(f"Symbol '{symbol}' is not valid or not found.")

    tick_size = symbol_info.trade_tick_size
    return tick_size

def open_calc(path: str= "static/calc.xlsx", sheetname: str= "United States"):
    calc = pd.read_excel(path, sheet_name=sheetname)
    return calc


def strtotimedate(dates: List[str], _format="%d/%m/%Y_%H:%M") -> pd.DatetimeIndex:
    '''
    Converts str datetimes to DatetimeIndex
    '''

    indexes = pd.DatetimeIndex(pd.to_datetime(dates, format=_format))

    return list(indexes)
            

def price_calc(open_, pip, multiplier):
    # log(type(open_), open_)
    # log(type(pip), pip)
    # log(type(multiplier), multiplier)

    price = round((pip*multiplier)+ open_, ndigits=4)
    return price

def isfloat(num):
    try:
        float(num.strip("[ , ]"))
        return True
    except ValueError:
        return False

def get_mean_var(string:str, sign=1):
    dirty_numbers = string.split(" ")
    # log(dirty_numbers)
    mean, var = [float(test.strip("[ , ]")) for test in dirty_numbers if isfloat(test) ]
  
    return sign*mean, sign*var
    dirty_numbers = string.split(" ")
    # log(dirty_numbers)
    mean, var = [float(test.strip("[ , ]")) for test in dirty_numbers if isfloat(test) ]
  
    return sign*mean, sign*var

def get_extra_points(df: pd.DataFrame, symbol: str, news: str, timeframe: int,
                     open_: float, time_open: pd.DatetimeIndex, multiplier: float,
                     function_over_price: Callable= lambda x: 2*x,
                     function_over_time: Callable= lambda x: x,) -> Dict[str, Tuple[pd.Timestamp]]:
    interest_row = df.loc[df["News"] == news+"_"+str(timeframe)].loc[df["Symbol"] == symbol]

    # log(interest_row.empty, end=', ')
    
    # log(news)

    positions = {"buy": {"Entry Point":None, "Estimated open position": None, "TP": None, "SL": None},
                "sell": {"Entry Point":None, "Estimated open position": None, "TP": None, "SL": None}}
    
    for position in ["buy", "sell"]:
        price_column, time_column, sign = ("Max_Open", 'Time_of_Max_Last_Year', 1) if position == 'sell' else ("Min_Open", 'Time_of_Min_Last_Year', -1)
        price_mean, price_var = get_mean_var(interest_row[price_column].iloc[0], sign)
        # log(type(open_), function_over_price(open_))

        time_mean, time_var = get_mean_var(interest_row[time_column].iloc[0])
        profit = float(interest_row["Profit"].iloc[0])
        # log(type(profit), profit)

        entry_point = price_calc(open_[position], function_over_price(price_mean), multiplier)
        # log(type(entry_point), entry_point)
        positions[position] = {'News': news, "Action": position.upper(),
                               "price_news_time": open_[position],
                               "Currency": symbol,
                               "EntryPoint": entry_point,
                               "TakeProfit": price_calc(entry_point, function_over_price(-1*sign*profit/2), multiplier),
                               "StepLoss": price_calc(open_[position], function_over_price(sign*profit/2), multiplier),
                               "EntryTime": (time_open + timedelta(minutes=time_mean)),
                               "WinRate": interest_row["Win Rate"].iloc[0]}
     
    return positions

def calc_position_size(symbol, entry, sl, risk):
     
    mt5.symbol_select(symbol, True)
    symbol_info = mt5.symbol_info(symbol)
    

    tick_size = symbol_info.trade_tick_size
    tick_value = symbol_info.trade_tick_value
    
    pips_at_risk  = np.abs(entry - sl) / tick_size

    
    lot = risk / (pips_at_risk * tick_value)

    if symbol=='XAUUSD': lot/=10 
    
    return np.round(lot, 2)

def strategy(df: pd.DataFrame, symbol: str, news: str, open_: float,
             time_open: pd.DatetimeIndex, multiplier: float, timeframe: float= 4, risk: int= 100):

    time_frame = {0.5: '30m', 1.0: '1h', 1.5: '1.5h', 2.0: '2h', 2.5: '2.5h', 3.0: '3h', 3.5: '3.5h', 4.0: '4h'}
    # log(timeframe, end=" : ")
    positions = get_extra_points(df=df, symbol=symbol, news=news,
                                      timeframe=timeframe, open_=open_, time_open=time_open, multiplier=multiplier)
    # log()
    info = [{"News": positions['buy']["News"], "Action": "Buy", "Currency": symbol,
            "TimeFrame": timeframe, "price_news_time": positions['buy']["price_news_time"],
            "TakeProfit": positions['buy']["price_news_time"], "StepLoss": positions['buy']["EntryPoint"], 
            "EntryTime": (positions['buy']["EntryTime"] + timedelta(minutes=10)).strftime("%d/%m/%Y %H:%M:%S"),
            "PendingTime": int((positions['buy']["EntryTime"] - time_open).total_seconds()),
            'RR': np.abs((positions['buy']["TakeProfit"] - positions['buy']["EntryPoint"]) / (positions['buy']["StepLoss"] - positions['buy']["EntryPoint"])),
            "WinRate": positions['buy']["WinRate"], 'PositionSize': calc_position_size(symbol, positions['buy']["EntryPoint"], positions['buy']["StepLoss"], risk),
            'Risk':risk},
            {"News": positions['sell']["News"], "Action": "Sell", "Currency": symbol,
            "TakeProfit": positions['sell']["price_news_time"], "StepLoss": positions['sell']["EntryPoint"], 
            "TimeFrame": timeframe, "price_news_time": positions['sell']["price_news_time"],
            "EntryTime": (positions['sell']["EntryTime"] + timedelta(minutes=10)).strftime("%d/%m/%Y %H:%M:%S"),
            "PendingTime": int((positions['sell']["EntryTime"] - time_open).total_seconds()),
            'RR': np.abs((positions['sell']["TakeProfit"] - positions['sell']["EntryPoint"]) / (positions['sell']["StepLoss"] - positions['sell']["EntryPoint"])),
            "WinRate": positions['sell']["WinRate"], 'PositionSize': calc_position_size(symbol, positions['sell']["EntryPoint"], positions['sell']["StepLoss"], risk),
            'Risk':risk}
            ]

    return info

def trade_on_news(initialize, news, country, risk, time_open, symbol=None, timeframe=None):
    calc_df = open_calc(path='static/MinMax Strategy Back Test.xlsx', sheetname=country)

    if timeframe == None or symbol == None:
        interest_rows = calc_df[calc_df['News'].str.contains(news, regex=False)]
        interest_rows.sort_values(by=['Win Rate', "Last 12 Profit"], ascending = False, inplace=True)
        symbol = interest_rows["Symbol"].iloc[0]
        timeframe = interest_rows["News"].iloc[0].split("_")[-1]
        log(f"best symbol and timeframe by winrate: {symbol} and {timeframe}")

    open_ = get_price(initialize, symbol)
    time_frame = {'30m':0.5,'1h': 1,'1.5h': 1.5, '2h': 2, '2.5h': 2.5, '3h': 3, '3.5h': 3.5, '4h': 4,
                  '0.5':0.5, '1': 1, "1.5": 1.5, '2': 2, "2.5": 2.5, "3": 3, "3.5": 3.5, "4": 4}
    
    
    positions= strategy(df= calc_df, symbol= symbol, news=news,
                        open_= open_, time_open=time_open,
                        multiplier=get_tick_size(symbol), timeframe=time_frame[timeframe], risk=risk)
    return positions

def trade_i_positions_on_news(initialize, news, country, risk, time_open, num_positions):
    calc_df = open_calc(path='static/MinMax Strategy Back Test.xlsx', sheetname=country)

    interest_rows = calc_df[calc_df['News'].str.contains(news, regex=False)]
    interest_rows.sort_values(by=['Win Rate', "Last 12 Profit"], ascending = False, inplace=True)
    interest_rows.drop_duplicates(subset=["Symbol"], keep='first', inplace=True)
    symbols = [interest_rows["Symbol"].iloc[i] for i in range(num_positions)]
    timeframes = [interest_rows["News"].iloc[i].split("_")[-1] for i in range(num_positions)]
    winrates = [interest_rows["Win Rate"].iloc[i] for i in range(num_positions)]
    log(f"country={country}, news={news}, symbol= {symbols}, timeframe={timeframes} with {winrates}")

    time_frame = {'30m':0.5,'1h': 1,'1.5h': 1.5, '2h': 2, '2.5h': 2.5, '3h': 3, '3.5h': 3.5, '4h': 4,
                  '0.5':0.5, '1': 1, "1.5": 1.5, '2': 2, "2.5": 2.5, "3": 3, "3.5": 3.5, "4": 4}
    
    positions = []
    for symbol, timeframe in zip(symbols, timeframes):
        open_ = get_price(initialize, symbol)
        positions.append(strategy(df= calc_df, symbol= symbol, news=news,
                            open_= open_, time_open=time_open,
                            multiplier=get_tick_size(symbol), timeframe=time_frame[timeframe], risk=risk))
    return positions


    