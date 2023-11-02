import sys
from time import sleep
import requests
import traceback
import pandas as pd
from datetime import datetime, timedelta

from get_data import get_today_calendar, create_positions_file, get_price
from strategy import Control_Position

import MetaTrader5 as mt5

from news_trading import trade_on_news, trade_i_positions_on_news
from utils import log

def news_trader(initialize, countries, symbol, timeframe, risk, timezone, num_positions=3):
    try:
        news_time = False
        positions = ()
        now = pd.Timestamp('today', tzinfo=timezone).replace(tzinfo=None)
        df = get_today_calendar(countries=countries, timezone=timezone)
        df_position, file_path = create_positions_file(timezone=timezone)
        # get df from now
        next_news = df[df["Date_Time"] > now].iloc[0]
        news_index = df[df["Date_Time"] > now].index[0]
        
        # if it's 5min before new, place position
        diff_now_next_news = datetime.strptime(str(next_news["Date_Time"]), "%Y-%m-%d %H:%M:%S") - now.replace(tzinfo=None)
        diff_now_last_news = now.replace(tzinfo=None) - datetime.strptime(str(df["Date_Time"].iloc[news_index-1]), "%Y-%m-%d %H:%M:%S")

        if timedelta(minutes=0) <= diff_now_next_news <= timedelta(minutes=5):
            news_time = True
            
            # positions = trade_on_news(initialize=initialize,
            #                           country=next_news['Country'], news=next_news['News'],
            #                           symbol= symbol, timeframe=timeframe, risk=risk, time_open=now)
            
            positions = trade_i_positions_on_news(initialize=initialize,
                                    country=next_news['Country'], news=next_news['News'],
                                    num_positions= num_positions, risk=risk, time_open=now)
            
            log(positions)
            # for position in positions:
            #     df_position = pd.concat([df_position, pd.DataFrame(position)], ignore_index=True)
            #     df_position.to_csv(file_path, index=False)
            for position in positions:
                Control_Position(initialize,  position)
           
                
        # if it's news is published to 4hour return true
        # if timedelta(minutes=0) <= diff_now_last_news <= timedelta(hours=4):
        #     news_time = True
        # elif timedelta(minutes=0) <= diff_now_next_news <= timedelta(minutes=21):
        #     news_time = True
        else:
            news_time = False
           
        # else return false
        
        return (news_time, positions)
    
    except AttributeError as e:
        if str(e) == "'NoneType' object has no attribute 'time'":
            log(f"An exception occurred:\n{traceback.format_exc()}")
            return None, None
        if str(e) == "'NoneType' object has no attribute 'profit'":
            log(f"An exception occurred:\n{traceback.format_exc()}")
            return None, None
        if str(e) == "'NoneType' object has no attribute 'ask'":
            log(f"An exception occurred:\n{traceback.format_exc()}")
            return None, None
        if str(e) == "'NoneType' object has no attribute 'bid'":
            log(f"An exception occurred:\n{traceback.format_exc()}")
            return None, None
        else:
            raise
    except requests.exceptions.JSONDecodeError as e:
        if str(e) == "Expecting value: line 1 column 1 (char 0)":
            log(f"An exception occurred:\n{traceback.format_exc()}")
            return None, None
        else:
            raise
    except IndexError as e:
        if str(e) == "single positional indexer is out-of-bounds":
            log(f"An exception occurred:\n{traceback.format_exc()}")
            return None, None
        else:
            raise
    except requests.exceptions.ConnectionError as e:
        log(f"An exception occurred:\n{traceback.format_exc()}")
        return None, None


def is_market_open(initialize):
    try:
        mt5.initialize()
        mt5.login(login=initialize[0], password=initialize[1],
                server=initialize[2])

        # get the symbol you want to check
        symbol = "EURUSD"

        # get the symbol info
        symbol_info = mt5.symbol_info(symbol)

        # check if the market is open for the symbol
        if symbol_info.time != 0:
            return True
        else:
            return False
    
    except AttributeError as e:
        if str(e) == "'NoneType' object has no attribute 'time'":
            log(f"An exception occurred:\n{traceback.format_exc()}")
            return False

    # shut down the connection to the MetaTrader 5 terminal
    # mt5.shutdown()

def run_bot(all_countries=['United States'], symbol=None, timeframe=None, risk=100, num_positions=3):
    message = "Starting Bot ..."
    log(message)
    while True:
        try:
            #initialize= ["51810268", "apmjgjp1", "Alpari-MT5-Demo"]
            initialize= ["51834380", "4wsirwes", "Alpari-MT5-Demo"]

            timezone = pytz.timezone('Asia/Tehran')
            market_status = is_market_open(initialize)

            if market_status == True:
                flag, positions = news_trader(initialize=initialize,
                        countries= all_countries,
                        symbol= symbol,
                        timeframe= timeframe,
                        risk= risk,
                        timezone= timezone,
                        num_positions= num_positions)
                # if positions != (): log(flag, positions)
                if flag != None:    
                    log(f"News Time? {'Yes' if flag else 'No'}")
                    for position in positions:
                        log(f'{{News: {position[0]["News"]}, TimeFrame: {position[0]["TimeFrame"]}, Currency: {position[0]["Currency"]}, Action: {position[0]["Action"]}, WinRate: {position[0]["WinRate"]}, RR: {position[0]["RR"]}, PositionSize: {position[0]["PositionSize"]}, TakeProfit: {position[0]["TakeProfit"]}, StepLoss: {position[0]["StepLoss"]}, EntryTime: {position[0]["EntryTime"]}, PendingTime: {position[0]["PendingTime"]}, Risk: {position[0]["Risk"]}}}')
                        log(f'{{News: {position[1]["News"]}, TimeFrame: {position[1]["TimeFrame"]}, Currency: {position[1]["Currency"]}, Action: {position[1]["Action"]}, WinRate: {position[1]["WinRate"]}, RR: {position[1]["RR"]}, PositionSize: {position[1]["PositionSize"]}, TakeProfit: {position[1]["TakeProfit"]}, StepLoss: {position[1]["StepLoss"]}, EntryTime: {position[1]["EntryTime"]}, PendingTime: {position[1]["PendingTime"]}, Risk: {position[1]["Risk"]}}}')
                    sleep(30)
                    if flag: sleep(5*60)
                else:
                    log(f"flag: {flag}, position:{positions}")
            else:
                log("market is closed")        
        except KeyboardInterrupt:
            # quit
            mt5.shutdown()
            sys.exit()

        # except AttributeError as e:
        #     if str(e) == "'NoneType' object has no attribute 'time'":
        #         log(f"An exception occurred:\n{traceback.format_exc()}")
        #         return run_bot(all_countries=all_countries, symbol=symbol,
        #                     timeframe=timeframe, risk=risk,
        #                     num_positions=num_positions)

    
       
if __name__ == "__main__":
    import pytz
    
    ########## test a news right now ##########
    # flag, positions = news_trader(initialize= ["51810268", "apmjgjp1", "Alpari-MT5-Demo"],
    #             countries= ['United States'],
    #             symbol= 'EURUSD',
    #             timeframe= '4h',
    #             risk= 100,
    #             timezone= pytz.timezone('Asia/Tehran'))

    # log(positions)

    ########### test a positions #############
    # trade_on_news(initialize= ["51810268", "apmjgjp1", "Alpari-MT5-Demo"],
    #               country='United States', news='OPEC Crude Oil Production Guinea',
    #               symbol= None, timeframe=None, risk=100, time_open=0)
    
    # # ############ test a random news ##############
    # from news_trading import open_calc, strategy, get_tick_size
    # from get_data import get_price
    # risk = 100
    # time_open = datetime.now()
    # country='United States'
    # news="10-Year Note Auction"
    # time_frame = {'30m':0.5,'1h': 1,'1.5h': 1.5, '2h': 2, '2.5h': 2.5, '3h': 3, '3.5h': 3.5, '4h': 4,
    #             '0.5':0.5, '1': 1, "1.5": 1.5, '2': 2, "2.5": 2.5, "3": 3, "3.5": 3.5, "4": 4}
    # calc_df = open_calc(path='static/MinMax Strategy Back Test.xlsx', sheetname=country)
    # # initialize = ["51545562", "zop7gsit", "Alpari-MT5-Demo"]
    # # initialize = ["51852441", "scfenm8n", "Alpari-MT5-Demo"]
    # initialize = ["51834380", "4wsirwes", "Alpari-MT5-Demo"]
    # mt5.initialize()
    # mt5.login(login=initialize[0], password=initialize[1], server=initialize[2])

    # interest_rows = calc_df[calc_df['News'].str.contains(news)]
    # interest_rows.sort_values(by=['Win Rate'], ascending = False, inplace=True)
    # symbol = interest_rows["Symbol"].iloc[0]
    # timeframe = interest_rows["News"].iloc[0].split("_")[-1]
    # open_ = get_price(initialize, symbol)
    # log(f"best symbol and timeframe by winrate: {symbol} and {timeframe}")

    # positions= strategy(df= calc_df, symbol= symbol, news=news,
    #                     open_= open_, time_open=time_open,
    #                     multiplier=get_tick_size(symbol), timeframe=time_frame[timeframe], risk=risk)
    # log(positions)
    # #testing saved dataframe
    # df = pd.DataFrame()
    # df = pd.concat([df, pd.DataFrame(positions)], ignore_index=True)
    # df.to_csv('test_positions_file.csv')  

    # # print(positions[0]['TimeFrame']*60*60)
    # # print(positions[1]['TimeFrame']*60*60)
    # Control_Position(initialize,  positions)
    ############## Test Multiplier Values ##############
    # import MetaTrader5 as mt5
    # from news_trading import get_tick_size
    # __MULTIPLIER__VALUE__ = { 
    #                     'AUDJPY': 0.1, 'AUDUSD': 0.00001, 'AUDCAD':0.001, 'AUDCHF': 0.001,
    #                     'CADCHF': 0.001, 'CADJPY': 0.1, 'CHFJPY': 0.1, 'GBPCHF': 0.001,
    #                     'EURAUD': 0.001, 'EURCAD': 0.001, 'EURGBP': 0.00001,
    #                     'EURJPY': 0.1, 'EURNZD': 0.001, 'EURUSD': 0.00001, 'EURCHF': 0.001, 
    #                     'GBPAUD': 0.001 , 'GBPJPY': 0.1, 'GBPUSD':0.00001, 'GBPCAD': 0.001,
    #                     'GBPNZD': 0.001, 
    #                     'NZDCAD': 0.001, 'NZDCHF': 0.001, 'NZDJPY': 0.1, 'NZDUSD': 0.001,
    #                     'USDCAD': 0.001, 'USDCHF': 0.001, 'USDJPY': 0.1,
    #                     'XAUUSD': 0.01, 
    #                     }
    # mt5.initialize()
    # # mt5.login(login="51545562", password="zop7gsit", 
    # #           server="Alpari-MT5-Demo")
    # new_mult = {symbol:get_tick_size(symbol) for symbol in __MULTIPLIER__VALUE__.keys()}    
    # print(new_mult)
    ##### Run the bot for a day #####
    run_bot(all_countries=['United States', 'United Kingdom', 'Euro Zone',
                           'Germany', 'Switzerland', 'Canada', 
                           'Australia', 'Japan', 'New Zealand', 'China'],
                           symbol=None, timeframe=None, risk=100, num_positions=3)

    



    



