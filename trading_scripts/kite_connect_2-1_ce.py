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
from configs.config import api_secret, api_key, tokens_ce, tickets_ce, \
    sell_margin, max_stop_loss, stop_loss_trail_margin, quantity, candle_duration
import uuid
import copy

print(sell_margin)
#logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('my-logger')
logger.propagate = False

status_file_path = status_file_path_ce
tokens = tokens_ce
tickets = tickets_ce

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


def exc_order(buy_at, sell_at, stop_loss, tk=tokens[0], current_price=None):
    global order_id, stop_loss_price, buying_price, selling_price, quantity
    t1 = time.time()
    order_id_b = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        tradingsymbol=tickets[tk],
        exchange=kite.EXCHANGE_NFO,
        transaction_type=kite.TRANSACTION_TYPE_BUY,
        quantity=quantity,
        order_type="MARKET",
        product=kite.PRODUCT_NRML,
    )
    dt = {}
    with open(status_file_path, 'r') as j:
        dt = json.loads(j.read())
    dt["already_buy"] = True
    with open(status_file_path, 'w') as f:
        json.dump(dt, f)

    ord_history = kite.order_history(order_id_b)[-1]
    if ord_history["status"] == "COMPLETE":
        buying_price = float(ord_history["average_price"])
        selling_price = float(ord_history["average_price"]) + 50
        stop_loss_price = buying_price-50
    else:
        return
    print(
        "order executed buy. at:", buying_price,
        "stop_loss:", stop_loss_price
    )
    buy_at, sell_at, stop_loss = buying_price, selling_price, stop_loss_price
    try:
        order_params = {
            "tradingsymbol": tickets[tk],
            "exchange": kite.EXCHANGE_NFO,
            "trigger_type": "two-leg",
            "trigger_values": [stop_loss, sell_at],
            "last_price": current_price,
            "orders": [
                {
                    "transaction_type": kite.TRANSACTION_TYPE_SELL,
                    "quantity": quantity,
                    "order_type": kite.ORDER_TYPE_SL,
                    "product": kite.PRODUCT_NRML,
                    "price": stop_loss
                },
                {
                    "transaction_type": kite.TRANSACTION_TYPE_SELL,
                    "quantity": quantity,
                    "order_type": kite.ORDER_TYPE_LIMIT,
                    "product": kite.PRODUCT_NRML,
                    "price": sell_at
                }
            ],
        }

        resp = kite.place_gtt(**order_params)
        order_id = resp['trigger_id']


    except Exception as e:
        logging.info("fail to place ggt order try with 10 stop loss")
        order_params = {
            "tradingsymbol": tickets[tk],
            "exchange": kite.EXCHANGE_NFO,
            "trigger_type": "two-leg",
            "trigger_values": [stop_loss, sell_at],
            "last_price": current_price,
            "orders": [
                {
                    "transaction_type": kite.TRANSACTION_TYPE_SELL,
                    "quantity": quantity,
                    "order_type": kite.ORDER_TYPE_SL,
                    "product": kite.PRODUCT_NRML,
                    "price": stop_loss
                },
                {
                    "transaction_type": kite.TRANSACTION_TYPE_SELL,
                    "quantity": quantity,
                    "order_type": kite.ORDER_TYPE_LIMIT,
                    "product": kite.PRODUCT_NRML,
                    "price": sell_at
                }
            ],
        }

        resp = kite.place_gtt(**order_params)
        order_id = resp['trigger_id']


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


def on_ticks(ws, ticks):
    global order_id
    # print("order_id", order_id)

    ticks = copy.deepcopy(ticks[0])
    if check_order_exited():
        try:
            with open(status_file_path, 'r') as j:
                data = json.loads(j.read())
                print(data, "current_price", ticks["last_price"])
        except Exception as e:
            return False

        if data["buy_status"] == True and data["buy_price"] < ticks["last_price"]:
            order_id = exc_order(
                buy_at=ticks["last_price"],
                sell_at=data["target_price"],
                stop_loss=data["stop_loss"],
                current_price=ticks["last_price"])
    else:
        trail_stop_loss(ticks["last_price"])


def on_connect(ws, response):
    pass


def on_close(ws, code, reason):
    ws.stop()


kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close
kws.connect(threaded=True)

x = kite.positions()

while True:
    if count < len(tokens):
        if kws.is_connected():
            kws.subscribe([tokens[count]])
            kws.set_mode(kws.MODE_FULL, [tokens[count]])
            count += 1
        else:
            logging.info("Connecting to WebSocket...")
