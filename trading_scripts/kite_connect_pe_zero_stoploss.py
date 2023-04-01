import logging
import time
from kiteconnect import KiteTicker
from datetime import datetime, timedelta
from pandas import DataFrame, read_csv, concat
from kiteconnect import KiteConnect
from trading_scripts.candle_structure import Candle
from utils.utils import get_access_token
from configs.config import api_secret, api_key
import uuid
import copy

logging.basicConfig(level=logging.DEBUG)


tokens = [11183106]
candle_duration = 5
sell_margin = 2
max_stop_loss = 20
stop_loss_trail_margin = 1
order_executed_at = None


buying_price = 0
selling_price = 0
stop_loss_price = 0
buy_flag = False
buy_status = False

first_target_hit = False
order_id = -999
first = "stage_1"

candle1 = Candle()
candle2 = Candle()
current_candle_start_time = datetime.now()
next_candle_start_time = datetime.now() + timedelta(minutes=candle_duration)


count = 0
order_detail = {
    "order_id": [0],
    "buy_at": [0],
    "min_target": [0],
    "stop_loss": [0],
    "status": [0],
    "profit": [0],
    "time": [datetime.now()]
}
orders = {}
order_file_name = str(datetime.now())+"_zero_pe_orders.csv"
df = DataFrame(order_detail)
df.to_csv(order_file_name, index=False)


access_token = "Bid4wPWLxXSQDPdrAz6aIPLqvVw16wLX"#get_access_token()
kws = KiteTicker(api_key, access_token)
kite = KiteConnect(api_key = api_key)
kite.set_access_token(access_token)

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
    if not buy_status:
        buy_flag = False
    return candle1, candle_temp



def print_candle(candle_name, candle_t):
    print(
        candle_name,
        "open : ", candle_t.open,
        "high : ", candle_t.high,
        "close : ", candle_t.close,
        "low : ", candle_t.low
    )



def trail_stop_loss(current_price):
    global first, current_candle_start_time, next_candle_start_time, candle_duration,\
        buy_flag, buying_price, selling_price, order_id, first_target_hit, sell_margin, stop_loss_price, \
        max_stop_loss, stop_loss_trail_margin, buy_status

    if order_id != -999:
        if current_price <= stop_loss_price:
            order_detail = {}
            order_detail["order_id"] = [order_id]
            order_detail["buy_at"] = [buying_price]
            order_detail["min_target"] = [buying_price + sell_margin]
            order_detail["stop_loss"] = [stop_loss_price]
            order_detail["status"] = ["exit"]
            order_detail["profit"] = [stop_loss_price - buying_price]
            order_detail["time"] = [datetime.now()]
            df = read_csv(order_file_name)
            df = concat([df, DataFrame(order_detail)])
            df.to_csv(order_file_name, index=False)
            print("*"*10, order_detail, "*"*10)

            buying_price = 0
            selling_price = 0
            stop_loss_price = 0
            buy_flag = False
            buy_status = False
            first_target_hit = False
            order_id = -999
            return True

        if first_target_hit is False:
            if current_price >= buying_price + sell_margin:
                stop_loss_price = current_price
                first_target_hit = True
                order_detail = {}
                order_detail["order_id"] = [order_id]
                order_detail["buy_at"] = [buying_price]
                order_detail["min_target"] = [buying_price + sell_margin]
                order_detail["stop_loss"] = [stop_loss_price]
                order_detail["status"] = ["SL_update"]
                order_detail["profit"] = [None]
                order_detail["time"] = [datetime.now()]

                df = read_csv(order_file_name)
                df = concat([df, DataFrame(order_detail)])
                df.to_csv(order_file_name, index=False)
                print("SL Order updated", order_detail)

                #update order

        if first_target_hit:
            if current_price-stop_loss_trail_margin >= stop_loss_price:
                stop_loss_price = current_price-stop_loss_trail_margin
                order_detail = {}
                order_detail["order_id"] = [order_id]
                order_detail["buy_at"] = [buying_price]
                order_detail["min_target"] = [buying_price + sell_margin]
                order_detail["stop_loss"] = [stop_loss_price]
                order_detail["status"] = ["SL_update"]
                order_detail["profit"] = [None]
                order_detail["time"] = [datetime.now()]
                df = read_csv(order_file_name)
                df = concat([df, DataFrame(order_detail)])
                df.to_csv(order_file_name, index=False)
                print("Order updated: ", "\n", order_detail)


def exc_order(buy_at,sell_at, stop_loss):
    global order_id, stop_loss_price, buying_price, selling_price
    order_id = uuid.uuid4()
    order_detail = {}
    order_detail["order_id"] = [order_id]
    order_detail["buy_at"] = [buy_at]
    order_detail["min_target"] = [sell_at]
    order_detail["stop_loss"] = [stop_loss]
    order_detail["status"] = ["buy"]
    order_detail["profit"] = [0]
    order_detail["time"] = [datetime.now()]
    df = read_csv(order_file_name)
    df = concat([df, DataFrame(order_detail)])
    df.to_csv(order_file_name, index=False)
    print("Order executed: ", "\n","buyPrice:", buy_at, " stop_loss: ", stop_loss)
    return order_id


def order_exited():
    if order_id == -999:
        return True
    return False


def on_ticks(ws, ticks):
    global first, current_candle_start_time, next_candle_start_time, candle_duration,\
        buy_flag, buying_price, selling_price, candle2, candle1, buy_status, stop_loss_price, \
        stop_loss_trail_margin, first_target_hit, order_id

    # Callback to receive ticks.
    #print(ticks)
    ticks = ticks[0]
    if first == "stage_1":
        if ticks["last_trade_time"].minute % candle_duration != 0:
            print("Waiting for first candle start", ticks["last_trade_time"], "candle_duration: ", candle_duration)
            return
        current_candle_start_time = ticks["last_trade_time"]
        next_candle_start_time = current_candle_start_time + timedelta(minutes=candle_duration)
        print(current_candle_start_time, next_candle_start_time)
        candle1.open = ticks["last_price"]
        candle1.high = ticks["last_price"]
        candle1.low = ticks["last_price"]
        candle1.close = ticks["last_price"]
        first = "stage_2"
        return
    elif first == "stage_2":
        print("start preparing first candle start", ticks["last_trade_time"], "candle_duration: ", candle_duration)
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

            first = "stage_3"
            current_candle_start_time = ticks["last_trade_time"]
            next_candle_start_time = current_candle_start_time + timedelta(minutes=candle_duration)

    #trail stoploss
    print("buy_price: ", buying_price, "buy_status: ", buy_status, "order_exited:", order_exited(), "buy_flags:", buy_flag)
    print_candle("candle1", candle1)
    print_candle("candle2", candle2)


    if order_id != -999:
        print("Order id:", order_id)
        print("*"*20,
            "buy price: ", buying_price,
            "min_target: ", selling_price,
            "stop_loss: ",stop_loss_price,
            "current price:", ticks["last_trade_time"]
        )

    if buy_status and order_exited():
        buy_flag = False
        buy_status = False
        buying_price = 0
        selling_price = 0
        stop_loss_price = 0
        first_target_hit = False
        order_id = -999
    if buy_status:
        #trail stoploss
        #if stoploss hits set buy status as False
        #update candle2
        #update current_candle_start_time  and next_candle_start_time
        #also if move to next candle then update cande also
        if ticks["last_trade_time"] < next_candle_start_time:
            trail_stop_loss(ticks["last_price"])
            candle2 = update_candle(candle2, ticks["last_price"])
            buy_status = True
        else:
            print("switch to next candle")
            trail_stop_loss(ticks["last_price"])
            current_candle_start_time = ticks["last_trade_time"]
            next_candle_start_time = current_candle_start_time + timedelta(minutes=candle_duration)
            candle1, candle2 = switch_candle(candle1, candle2, ticks["last_price"])
            return

    #if buy status not triggerg then check and triggerd
    if buy_status == False:
        if ticks["last_trade_time"] < next_candle_start_time:
            if buy_flag:
                    # if max(candle1.open, candle1.close) >= ticks["last_price"]:
                    order_id = exc_order(
                        buy_at=ticks["last_price"],
                        sell_at=ticks["last_price"] + sell_margin,
                        stop_loss=0
                    )
                    buying_price = ticks["last_price"]
                    selling_price = ticks["last_price"] + sell_margin
                    stop_loss_price = ticks["last_price"]-1
                    buy_status = True

            if buy_flag == False:
                if candle1.high < ticks["last_price"]:
                    buy_flag = True
                    print("buy_flag is set to be true")
                    print("order should be executed at: ", candle1.open)
            candle2 = update_candle(candle2, ticks["last_price"])
        else:
            buy_flag = False
            current_candle_start_time = ticks["last_trade_time"]
            next_candle_start_time = current_candle_start_time + timedelta(minutes=candle_duration)
            candle1, candle2 = switch_candle(candle1, candle2, ticks["last_price"])
            if candle1.high < ticks["last_price"]:
                buy_flag = True
            return

    #logging.debug("Ticks: {}".format(ticks))

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

# Assign the callbacks.
# kws.on_ticks = on_ticks
# kws.on_connect = on_connect
# kws.on_close = on_close

# Infinite loop on the main thread. Nothing after this will run.
# You have to use the pre-defined callbacks to manage subscriptions.
# kws.connect(threaded=True)

# while True:
#     if count < len(tokens):
#         if kws.is_connected():
#             kws.subscribe([tokens[count]])
#             kws.set_mode(kws.MODE_FULL, [tokens[count]])
#             count += 1
#         else:
#             logging.info("Connecting to WebSocket...")
from pandas import read_csv, to_datetime
dft = read_csv("/Users/mukul/PycharmProjects/AutomateTrading/configs/current_trading_data22.csv", on_bad_lines='skip')
dft = dft[dft["instrument_token"]==11183106]
dft.last_trade_time = to_datetime(dft.last_trade_time)
dft["last_price"]= dft["last_price"]

dft = dft.to_dict("records")
for i in dft:
    on_ticks("", [i])

ddd= read_csv("/Users/mukul/PycharmProjects/AutomateTrading/trading_scripts/2023-02-15 12:56:42.012561_zero_pe_orders.csv")
print()



