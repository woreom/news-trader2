## Import Libraries
import os
from typing import List
import glob
import pytz
from datetime import datetime, timedelta
from time import sleep

import numpy as np
import pandas as pd
import investpy
import MetaTrader5 as mt5
import time

from utils import log

def current_time():
    
    df = pd.DataFrame(mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M1, 0, 10))

    df['time']=pd.to_datetime(df['time'], unit='s')
    
    return df['time'].iloc[-1]

def get_price_at_minmax_time(initialize, symbol, sleep_time, action):
    # Initialization
    if action == "buy":
        sleep(sleep_time)
        mt5.initialize()
        mt5.login(login=initialize[0],password=initialize[1],server=initialize[2])
        return mt5.symbol_info_tick(symbol).ask
    elif action == "sell":
        sleep(sleep_time) 
        mt5.initialize()
        mt5.login(login=initialize[0],password=initialize[1],server=initialize[2])
        return mt5.symbol_info_tick(symbol).bid
    else:
        print('position is failed')


def get_price(initialize, symbol):
    # Initialization
    mt5.initialize()
    mt5.login(login=initialize[0],password=initialize[1],server=initialize[2])
    
    for _ in range(3):
        
        # ask = mt5.symbol_info_tick(symbol).ask
        # bid = mt5.symbol_info_tick(symbol).bid

        df = get_data_from_mt5(initialize=initialize, Ticker=symbol, TimeFrame='5m')
        price = df.iloc[-1]['Open']
        ask = price
        bid = price

    return {"buy": ask, "sell": bid}

def get_candle(initialize: List, symbol: str, timeframe: str) -> pd.DataFrame:
    
    for _ in range(3):
        df = get_data_from_mt5(initialize=initialize, Ticker=symbol, TimeFrame=timeframe)
        last_candle = df.iloc[-1]
    return last_candle

def get_ask(initialize: List, symbol: str) -> float:
    # Initialization
    mt5.initialize()
    mt5.login(login=initialize[0],password=initialize[1],server=initialize[2])
    
    for _ in range(3):
        ask = mt5.symbol_info_tick(symbol).ask

    return ask

def get_bid(initialize: List, symbol: str) -> float:
    # Initialization
    mt5.initialize()
    mt5.login(login=initialize[0],password=initialize[1],server=initialize[2])
    
    for _ in range(3):
        bid = mt5.symbol_info_tick(symbol).bid

    return bid

def get_open_positions(initialize: List) -> pd.DataFrame:
    # Initialization
    mt5.initialize()
    mt5.login(login=initialize[0],password=initialize[1],server=initialize[2])

    trade_positions = mt5.positions_get()
    if trade_positions is None:
        return pd.DataFrame()
    else:
        # Get Open Positions from MT5
        open_positions = pd.DataFrame(list(trade_positions),columns=trade_positions[0]._asdict().keys())
        # Replace time from seconds to datetime format
        open_positions['time'] = pd.to_datetime(open_positions['time'], unit='s')
        open_positions['time_update'] = pd.to_datetime(open_positions['time_update'], unit='s')
        # Drop time in miliseconds
        open_positions.drop(['time_msc', 'time_update_msc'], axis=1, inplace=True)
        # Replace 1 with Sell
        open_positions.loc[open_positions['type']==1, 'type'] = 'Sell'
        # Replace 0 with Buy
        open_positions.loc[open_positions['type']==0, 'type'] = 'Buy'
        # Replace type with action
        open_positions["action"] = open_positions["type"].copy()
        open_positions.drop(['type'], axis=1, inplace=True)
        
        return open_positions


## Download historical market data from MetaTrader5
def get_data_from_mt5(initialize, Ticker, TimeFrame):
    """
    Download historical market data from MetaTrader5.
    
    Parameters:
        initialize: A list containing the login credentials and server information for the MetaTrader5 account.
        The list should be in the format [login, password, server].
        Ticker: A string representing the currency ticker to download.
        TimeFrame: A string representing the time frame of the data to download. 
        Valid values are "1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w".
    
    Returns:
        A pandas DataFrame containing the historical market data.
    
    Examples:
        # Download historical market data from MetaTrader5
        initialize = [123456, 'password', 'MetaTraderServer']
        Ticker = 'EURUSD'
        TimeFrame = '1h'
        data = get_data_from_mt5(initialize, Ticker, TimeFrame)
    """

    # Initialization
    mt5.initialize()
    mt5.login(login=initialize[0],password=initialize[1],server=initialize[2])
    
    
    # Time Frames Definition
    TimeFrames={
                "1m":mt5.TIMEFRAME_M1,
                "5m":mt5.TIMEFRAME_M5,
                "15m":mt5.TIMEFRAME_M15,
                "30m":mt5.TIMEFRAME_M30,
                "1h":mt5.TIMEFRAME_H1,
                "4h":mt5.TIMEFRAME_H4,
                "1d":mt5.TIMEFRAME_D1,
                "1w":mt5.TIMEFRAME_W1,
                }
                

    # Get Data and do Some Proccess
    df = pd.DataFrame(mt5.copy_rates_from_pos(Ticker,  TimeFrames[TimeFrame], 0, 99999))

    df['time']=pd.to_datetime(df['time'], unit='s')
    df.set_index(df['time'],inplace=True)
    df.index = df.index.tz_localize(None)
    del df['time'],df['spread'],df['real_volume']
    df.columns=['Open', 'High', 'Low', 'Close', 'Volume']
    df['Mean']=np.mean(pd.concat((df['Low'],df['High'], df['Close']),axis=1),axis=1)
    df['diff']=df['Mean']-df['Mean'].shift(1)
    df['info']=f'{Ticker}_{TimeFrame}'

    return df

## Read Investing data
def clean_investing_data(df):
    
    # Set index to date
    df.index = pd.to_datetime(df["Date"])
    
    # Sort DataFrame by index
    df.sort_index(axis=0, ascending=True, inplace=True)
    
    # Rename 'Price' column to 'Close' for consistency
    df['Close'] = df['Price']
    
    # Drop unnecessary columns
    try:
        df = df.drop(columns=["Date", "Change %", "Vol.", "Price"])
    except:
        df = df.drop(columns=["Date", "Change %", "Price"])
    
    try: 
        df = df.drop(columns=['Unnamed: 0'])
    except: 
        pass
        
    
    # Clean data by removing commas and converting to float
    for column in df.columns:
        for k in range(len(df[column])):
            if type(df[column][k]) == str:
                df[column][k] = df[column][k].replace(",","")
        df[column] = df[column].astype(float)   
    

    df['Mean'] = np.mean(pd.concat((df['Low'], df['High'], df['Close']), axis=1), axis=1)
    df['diff'] = df['Mean'] - df['Mean'].shift(1)
    df = df.loc[~df.index.duplicated()]
    return df.dropna()

def get_country_index_from_investing(country):
    
    dxy =pd.read_csv("static/investing_data/USD/US Dollar Index.csv")
    dxy = clean_investing_data(dxy)
    if country == 'USD':
        country_index =dxy

    else:
        if country in ['CAD', 'JPY', 'SEK', 'CHF']:
            Ticker = 'USD' + country
            df = pd.read_csv(f"static/investing_data/{country}/{Ticker}.csv")
            df = clean_investing_data(df)
            df=df[['Open', 'High', 'Low', 'Close']]
            country_index = dxy/df
        else:
            Ticker = country + 'USD'
            df = pd.read_csv(f"static/investing_data/{country}/{Ticker}.csv")
            df = clean_investing_data(df)
            df=df[['Open', 'High', 'Low', 'Close']]
            country_index = df*dxy
            
        country_index['Mean']=np.mean(pd.concat((country_index['Low'],country_index['High'], country_index['Close']),axis=1),axis=1)
        country_index['diff']=country_index['Mean']-country_index['Mean'].shift(1)
    
    return country_index.dropna()

def get_csv_files(country):
    """
    A function that returns a list of CSV files in the directory for the given country.

    Parameters:
    country (str): the name of the country for which to retrieve the CSV files.

    Returns:
    csv_files (list): a list of CSV files in the directory for the given country, without the '.csv' file extension.

    """
    current = os.getcwd()
    path = os.path.join(current, 'static','investing_data', country)
    extension = 'csv'
    os.chdir(path)
    csv_files = [os.path.splitext(file)[0] for file in glob.glob(f'*.{extension}')]
    os.chdir(current)
    return csv_files


def clean_news(df):
    news = []
    
    for row in df['News']:
        parts = []
        news_parts = row.split(" ")
        #clean empty spaces
        news_parts = list(filter(("").__ne__, news_parts))
        #clean extra months
        for part in news_parts:
            if "(" in part:
                if part in ["(YoY)", "(MoM)"]:
                    parts.append(part)
            elif part == "\xa0":
                parts.insert(0, "Flash")
            
            else:
                parts.append(part)
        news.append(" ".join(parts))
    
    return news

def fix_dataframe(tf:pd.DataFrame):
    df = tf[tf["currency"].notna()]
    
    df = df.drop(df.loc[df['time']=='Tentative'].index, inplace=False)
    
    df.drop(df.loc[df['time']=='All Day'].index, inplace=True)
    
    
    df["Date_Time"]= pd.to_datetime(df["date"] + " " + df["time"], format='%d/%m/%Y %H:%M')
    
    df[["Impact", 'News', 'Country', 'Actual', 'Forecast', "Previous"]] = df[["importance", 'event', 'zone', 'actual', 'forecast', "previous"]]
    
    df.drop(columns=['id', 'date', 'time', "zone", "currency", "importance", 'event', 'actual', 'forecast', "previous"], inplace=True)
        
    df.sort_values('Date_Time', axis=0, ascending=True, inplace=True)
    
    
    removed_objects=' ,!KkBbMmTt  %'

    F = lambda name: [row if pd.isnull(row) else row.translate({ord(i): None for i in removed_objects}) for row in df[name]]
    G = lambda name: [row if pd.isnull(row) else row.translate({ord(i): None for i in removed_objects}) for row in df[name]]

    df["Actual"] = F("Actual")
    df["Forecast"] = F("Forecast")
    df["Previous"] = F("Previous")
    df[["Actual", "Forecast", "Previous"]] = df[["Actual", "Forecast", "Previous"]].astype("float64")
    
    df["News"] = clean_news(df)
    df["Country"] = [c.title() for c in df["Country"]]
    df = df[["Date_Time", 'News', 'Country', 'Actual', 'Forecast', "Previous"]]
    
    return df


def convert_to_gmt(requested_time):
    offset = requested_time.strftime('%z')
    return f"GMT {offset[0]}{offset[1] if offset[1]!= '0' else '' }{offset[2]}:{offset[3]}{offset[4]}"

def create_positions_file(timezone):
    columns = {'News': '', 'Action': '', 'Currency': '', 'EntryPoint': '', 'TimeFrame': '', 'TakeProfit': '',
    'StepLoss': '',  'EntryTime': '',  'PendingTime': '', 'RR': '', 'WinRate': '', 'PositionSize': '', 'Risk': ''}
    now = datetime.now(timezone)
    file_path=f'static/{now.strftime("%Y-%m-%d")}_positions.csv'
    if os.path.exists(file_path):
        df_positions = pd.read_csv(file_path)
    else:    
        df_positions = pd.DataFrame(columns=columns)    
        df_positions.to_csv(file_path, index=False)
        
    return df_positions, file_path


def get_today_calendar(countries: List, timezone):
    
    now = datetime.now(timezone)
    print(now)
    #file_path=f'static/{now.date().strftime("%m-%d-%Y_%H")}.xlsx'
    file_path=f'static/{now.strftime("%Y-%m-%d_%H")}.xlsx'
    
    print(file_path)
    if os.path.exists(file_path):
        return pd.read_excel(file_path)
    gmt_format = convert_to_gmt(now)

    # countries = ["United States", "Australia","Japan", "Euro Zone", "Germany", 
    #     "United Kingdom", "New Zealand", "Canada", "Switzerland"]

    df = investpy.news.economic_calendar(time_zone=gmt_format, countries=countries,
                                        importances=["high", "medium", "low"],
                                        from_date=now.strftime("%d/%m/%Y"),
                                        to_date=(now + timedelta(hours=24)).strftime("%d/%m/%Y"),
                                        )
    
    df = fix_dataframe(tf=df)
    # print(df)
    df.to_excel(f'static/{now.strftime("%Y-%m-%d_%H")}.xlsx',index=False)
    return df


def make_folder(path):
    if not os.path.exists(path):
        os.mkdir(path)

def merge_dataframes(path):
    
    li = [pd.read_csv(file, index_col=0) for file in glob(path)]
    df = pd.concat(li, axis=0, ignore_index=True)
    df.sort_values(["Date_Time"], axis=0, ascending=True, inplace=True)
    df.reset_index(inplace=True)
    df = df.drop(columns=["index"])

    return df

def get_calendar_historical_data(from_year:int= 2008, to_year:int= 2022, to_date:str="05/08",
             save_path="static",
             countries:List[str]=["United States", "Euro Zone", "Canada", "united kingdom"],):
    
    # if save_path in ["", "."]:
    #     save_path = os.path.abspath('.')
    
    temp_path = os.path.join(save_path, "temp")
    make_folder(temp_path)
    for country in countries:
        country_path = os.path.join(temp_path, country)
        make_folder(country_path)
        
        i = from_year
        while i < to_year:
            try:
                df = investpy.news.economic_calendar(time_zone="GMT -5:00", countries=[country],
                                    importances=["high", "medium", "low"],
                                    from_date="01/01/"+str(i),
                                    to_date="01/01/"+str(i+1))
                
                df = fix_dataframe(df)
                df.to_csv(os.path.join(country_path, f"{country}_{i}_{i+1}_all_news.csv"))
                log(f"Saved calendar from {i} to {i+1} at {country_path}")
                i+=1
            except:
                pass
        
        i=0
        while i == 0:
            try:
                df = investpy.news.economic_calendar(time_zone="GMT -5:00", countries=[country],
                                    importances=["high", "medium", "low"],
                                    from_date="01/01/"+str(to_year),
                                    to_date=str(to_date)+"/"+str(to_year))
                
                df = fix_dataframe(df)
                df.to_csv(os.path.join(country_path, f"{country}_{to_year}_all_news.csv"))
                log(f"Saved calendar from 01/01/{to_year} to {to_date}/{to_year} at {country_path}")
                i+=1
            except:
                pass
            
       
        df = merge_dataframes(os.path.join(country_path, "*.csv"))
        df.to_csv(os.path.join(save_path, country+"_all_news.csv"))
        
    ## removes not empty directory and its content
    # shutil.rmtree(temp_path)

            
    log("Done!")


