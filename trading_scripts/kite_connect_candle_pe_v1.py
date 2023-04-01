import json
import logging
import time
from kiteconnect import KiteTicker
from datetime import datetime, timedelta
from pandas import DataFrame, read_csv, concat
from kiteconnect import KiteConnect
from trading_scripts.candle_structure import Candle
from utils.utils import get_access_token
from configs.config import api_secret, api_key, status_file_path_pe
import uuid
import copy
from configs.config import tokens_ce, tokens_pe, stop_loss_trail_margin, sell_margin, max_stop_loss

logging.basicConfig(level=logging.DEBUG)
stop_loss_price =0
first = "stage_1"
stage1 = 0
tokens = tokens_pe
status_file_path = status_file_path_pe

with open(status_file_path, 'w') as f:
    data = {
        "buy_status": False,
        "buy_price": 0,
        "stop_loss": 0,
        "target_price": 0,
    }
    json.dump(data, f)

candle_duration = 5
candle1 = Candle()
candle2 = Candle()
current_candle_start_time = datetime.now()
next_candle_start_time = datetime.now() + timedelta(minutes=candle_duration)
count = 0
access_token = get_access_token()


kws = KiteTicker(api_key, access_token)
# kite = KiteConnect(api_key = api_key)
# kite.set_access_token(access_token)

def update_candle(candle_t, current_price):
    if current_price > candle_t.high:
        candle_t.high = current_price
    if current_price < candle_t.low:
        candle_t.low = current_price
    candle_t.close = current_price
    return candle_t


def switch_candle(candle1, candle2, price):
    global buy_flag, buy_status
    candle1.open = candle2.open
    candle1.high = candle2.high
    candle1.close = candle2.close
    candle1.low = candle2.low
    del candle2
    candle_temp = Candle()
    candle_temp.open = price
    candle_temp.high = price
    candle_temp.low = price
    candle_temp.close = price

    return candle1, candle_temp



def print_candle(candle_name, candle_t):
    print(
        candle_name,
        "open : ", candle_t.open,
        "high : ", candle_t.high,
        "close : ", candle_t.close,
        "low : ", candle_t.low
    )


def save_ticke():
    global df


def on_ticks(ws, ticks):
    global first, current_candle_start_time, next_candle_start_time, candle_duration,\
        candle2, candle1, stage1

    # Callback to receive ticks.
    #print(ticks)
    ticks = copy.deepcopy(ticks[0])
    # with open(datetime.today().date().strftime("%d-%m-%Y")+"_", "a+"):
    #

    if stage1 == 0:
        if first == "stage_1":
            if ticks["last_trade_time"].minute % candle_duration != 0:
                # print("Waiting for first candle start", ticks["last_trade_time"], "candle_duration: ", candle_duration)
                return
            current_candle_start_time = ticks["last_trade_time"]
            next_candle_start_time = current_candle_start_time + timedelta(minutes=candle_duration)
            # print(current_candle_start_time, next_candle_start_time)
            candle1.open = ticks["last_price"]
            candle1.high = ticks["last_price"]
            candle1.low = ticks["last_price"]
            candle1.close = ticks["last_price"]
            first = "stage_2"
            return
        elif first == "stage_2":
            # print("start preparing first candle start", ticks["last_trade_time"], "candle_duration: ", candle_duration)
            if ticks["last_trade_time"] < next_candle_start_time:
                candle1 = update_candle(candle1, ticks["last_price"])
                print_candle("candle1", candle1)
                return
            else:
                print("first candle done", ticks["last_trade_time"], "candle_duration: ", candle_duration)
                print("switch to next candle")
                candle2 = Candle()
                candle2.open = ticks["last_price"]
                candle2.high = ticks["last_price"]
                candle2.low = ticks["last_price"]
                candle2.close = ticks["last_price"]
                stage1 = 2
                first = "stage_3"
                current_candle_start_time = ticks["last_trade_time"]
                next_candle_start_time = current_candle_start_time + timedelta(minutes=candle_duration)


    print_candle("candle1", candle1)
    print_candle("candle2", candle2)



    if ticks["last_trade_time"] < next_candle_start_time:
        candle2 = update_candle(candle2, ticks["last_price"])
        if ticks["last_price"]-4 >= candle1.high:
            with open(status_file_path, 'w') as f:
                data = {
                    "buy_status": True,
                    "buy_price": candle1.high,
                    "stop_loss": candle1.high - 2,
                    "target_price": candle1.high + sell_margin,

                }
                json.dump(data, f)
        elif ticks["last_price"] < candle1.high:
            with open(status_file_path, 'w') as f:
                data = {
                    "buy_status": False,
                    "buy_price": 0,
                    "stop_loss": 0,
                    "target_price": 0,
                }
                json.dump(data, f)
    else:
        # print("switch to next candle")
        current_candle_start_time = ticks["last_trade_time"]
        next_candle_start_time = current_candle_start_time + timedelta(minutes=candle_duration)
        candle1, candle2 = switch_candle(candle1, candle2, ticks["last_price"])
        if ticks["last_price"] - 4 >= candle1.high:
            with open(status_file_path, 'w') as f:
                data = {
                    "buy_status": True,
                    "buy_price": candle1.high,
                    "stop_loss": candle1.high - 2,
                    "target_price": candle1.high + sell_margin,
                }
                json.dump(data, f)
        else:
            with open(status_file_path, 'w') as f:
                data = {
                    "buy_status": False,
                    "buy_price": 0,
                    "stop_loss": 0,
                    "target_price": 0,
                }
                json.dump(data, f)
        return


def on_connect(ws, response):
    pass
    # Callback on successful connect.
    # Subscribe to a list of instrument_tokens (RELIANCE and ACC here).
    #ws.subscribe([ce_code])

    # Set RELIANCE to tick in `full` mode.
    #ws.set_mode(ws.MODE_FULL, [ce_code])

    # global current_candle_no, dt_
    # dt = datetime.now()
    # year = dt.year
    # month = dt.month
    # day = dt.day
    # hours = dt.hour
    # minutes = dt.minute - int(dt.minute % 5)
    # dtt = datetime(year, month, day, hours, minutes)
    # if dtt < datetime(year, month, day, 9, 15) or dtt > datetime(year, month, day, 15, 25):
    #     current_candle_no = 1
    # else:
    #     current_candle_no = dt_.index(dtt)



def on_close(ws, code, reason):
    # On connection close stop the main loop
    # Reconnection will not happen after executing `ws.stop()`
    ws.stop()

#Assign the callbacks.
kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close
kws.connect(threaded=True)

while True:
    if count < len(tokens):
        if kws.is_connected():
            kws.subscribe([tokens[count]])
            kws.set_mode(kws.MODE_FULL, [tokens[count]])
            count += 1
        else:
            logging.info("Connecting to WebSocket...")
