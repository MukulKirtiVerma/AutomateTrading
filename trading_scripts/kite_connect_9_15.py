import json
import logging
import threading
import time
from kiteconnect import KiteTicker
from datetime import datetime, timedelta
from pandas import DataFrame, read_csv, concat, read_json, read_pickle
from kiteconnect import KiteConnect
from scipy.cluster.hierarchy import complete

from trading_scripts.candle_structure import Candle
from configs.config import status_file_path_ce
from utils.utils import get_access_token
from configs.config import api_secret, api_key, tokens_ce, tickets_ce, tickets, \
    sell_margin, max_stop_loss, stop_loss_trail_margin, quantity, candle_duration
import uuid
import copy
from apscheduler.schedulers.blocking import BlockingScheduler
# Initialise KiteConnect client



# define the task to be executed
def update_token():
    get_access_token()


print(sell_margin)
#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('my-logger')
logger.propagate = False

status_file_path = status_file_path_ce
tokens = list(tickets.keys())
tickets = tickets

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

access_token = get_access_token()
kws = KiteTicker(api_key, access_token)
kite = KiteConnect(api_key = api_key)
kite.set_access_token(access_token)




def check_order_exited_():
    global order_id, buying_price, selling_price, stop_loss_price
    oreder_history = kite.order_history(order_id)[-1]
    while True:
        time.sleep(0.1)
        # print("current:", order_id, "status",oreder_history["status"], "stop_loss_price", stop_loss_price)
        if oreder_history["status"] == "COMPLETE":
            print("####################################stoploss hit:", "buying price",buying_price,
                  "stop_loss_price", oreder_history["average_price"])
            buying_price = 0
            selling_price = 0
            stop_loss_price = 0
            order_id = -999
            break


def trail_stop_loss(current_price, tk=tokens[0]):
    global first, current_candle_start_time, next_candle_start_time, candle_duration, \
        buy_flag, buying_price, selling_price, order_id, first_target_hit, sell_margin, stop_loss_price, \
        max_stop_loss, stop_loss_trail_margin, buy_status
    if order_id != -999:
        print(
            "buying: ", buying_price,
            "current_price", current_price,
            "stoploss: ", stop_loss_price,
            "target : ", buying_price + sell_margin
        )
        if current_price >= selling_price - stop_loss_trail_margin:
            temp_stop_loss = current_price - 5
            temp_selling_price = current_price + sell_margin
            print(
                "try to update stop loss\n buying: ", buying_price,
                "current_price", current_price,
                "stoploss: ", stop_loss_price,
                "target : ", selling_price,
                "try to set stop_loss at :", temp_stop_loss,
                "try to set selling price at :", temp_selling_price
            )

            try:
                if order_id != -999:
                    new_order_params = {
                        "tradingsymbol": tickets[tk],
                        "exchange": kite.EXCHANGE_NFO,
                        "trigger_type": "two-leg",
                        "last_price": current_price,
                        "trigger_values": [temp_stop_loss, temp_selling_price],
                        "orders": [
                            {
                                "transaction_type": kite.TRANSACTION_TYPE_SELL,
                                "quantity": quantity,
                                "order_type": kite.ORDER_TYPE_SL,
                                "product": kite.PRODUCT_NRML,
                                "price": temp_stop_loss
                            },
                            {
                                "transaction_type": kite.TRANSACTION_TYPE_SELL,
                                "quantity": quantity,
                                "order_type": kite.ORDER_TYPE_LIMIT,
                                "product": kite.PRODUCT_NRML,
                                "price": temp_selling_price
                            }
                        ]
                    }

                    # Modify the GTT order
                    response = kite.modify_gtt(order_id, **new_order_params)
                    if response['status'] == "success":
                        stop_loss_price = temp_stop_loss
                        selling_price = temp_selling_price
                        print("GTT order updated")
                        print(
                            "buying price: ", buying_price,
                            "current_price", current_price,
                            "stoploss: ", stop_loss_price,
                            "target : ", selling_price,
                        )

            except Exception as e:
                print("fail to update gtt {e}")


def exc_order(buy_at, tk=tokens[0]):
    try:
        global order_id, stop_loss_price, buying_price, selling_price, quantity
        t1 = time.time()
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            tradingsymbol=tickets[tk],
            exchange=kite.EXCHANGE_NFO,
            transaction_type=kite.TRANSACTION_TYPE_BUY,
            quantity=quantity,
            price=buy_at,
            order_type=kite.ORDER_TYPE_SL,
            product=kite.PRODUCT_NRML,
        )
        print(order_id)
    except:
        pass


    return order_id


def order_exited():
    if order_id == -999:
        return True
    return False

def check_order_exited():
    global order_id, buying_price, selling_price, stop_loss_price, tokens
    resp = kite.positions()['net']
    token = tokens[0]
    pos_id = {}
    if len(resp) > 0:
        for pos in resp:
            if token == pos["instrument_token"]:
                pos_id = pos
                break
    else:
        buying_price = 0
        selling_price = 0
        stop_loss_price = 0
        order_id = -999
        return True

    if len(pos_id)>0:
        if pos_id["quantity"] > 0:
            return False
        else:
            buying_price = 0
            selling_price = 0
            stop_loss_price = 0
            order_id = -999
            return True

    else:
        buying_price = 0
        selling_price = 0
        stop_loss_price = 0
        order_id = -999
        return True





    # oreder_history = kite.order_history(order_id)[-1]
    # # print("current:", order_id, "status",oreder_history["status"], "stop_loss_price", stop_loss_price)
    # if oreder_history["status"] == "COMPLETE":
    #     # print("stoploss hit:", order_id,
    #     #       "status", oreder_history["status"],
    #     #       "stop_loss_price", oreder_history["average_price"])
    #     buying_price = 0
    #     selling_price = 0
    #     stop_loss_price = 0
    #     order_id = -999
    #     return True
    # return False


def exit_order():
    global order_id

is_active = True

def on_ticks(ws, ticks):
    global order_id, is_active
    # print("order_id", order_id)
    try:
        ticks_1 = copy.deepcopy(ticks[0])
        ticks_2 = copy.deepcopy(ticks[1])
        if is_active and ticks[0]["last_trade_time"]>=datetime(
                datetime.today().year,
                datetime.today().month,
                datetime.today().day,
                9, 15, 0
        ):

            order_id_1 = exc_order(
                buy_at=ticks_1["last_price"] + 10,
                tk=ticks_1["instrument_token"])
            order_id_2 = exc_order(
                buy_at=ticks_2["last_price"] + 10,
                tk=ticks_2["instrument_token"]
            )
            is_active = False

    except:
        print("No order exec", ticks)




def on_connect(ws, response):
    pass


def on_close(ws, code, reason):
    ws.stop()


kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close
kws.connect(threaded=True)
tokens = list(tickets.keys())
tickets = tickets


# x = kite.positions()
# kite.instruments()
while True:
    if count < len(tokens):
        if kws.is_connected():
            kws.subscribe([tokens[count]])
            kws.set_mode(kws.MODE_FULL, [tokens[count]])
            count += 1
        else:
            logging.info("Connecting to WebSocket...")
