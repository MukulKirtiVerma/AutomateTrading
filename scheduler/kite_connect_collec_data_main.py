import logging
import os
import threading
import apscheduler
import time
import requests
from kiteconnect import KiteTicker
from datetime import datetime, timedelta
from pandas import DataFrame, read_csv, concat
from kiteconnect import KiteConnect
from configs.config import api_secret, api_key
logging.basicConfig(level=logging.DEBUG)

from configs.config import api_secret, api_key, tickets_ce, tickets_pe

tokens = list(tickets_ce.keys()) + list(tickets_pe.keys())




api_key="gft6amzyywoorxa9"
api_secret="70ik8sezbdeg618bkwz440yp4v8yrs5j"
totp_secret="DBJ3X7IMZ5UEKSSW4A7AISF7HK46CRWS"
user_id="PDC829"
password="mukul@123"


def get_access_token(
        api_key=api_key,
        user_id=user_id,
        password=password,
        totp_secret=totp_secret
):
    access_token = ""
    access_token_file = open('../configs/access_token.txt', 'r')
    token_info = access_token_file.readlines()
    today_date = str(datetime.now().strftime("%Y-%m-%d") + "\n")
    if len(token_info) == 2 and token_info[0] == today_date:
        access_token = token_info[1]
        print("Today's Token already available: ", access_token)
        return access_token

def generate_access_token():
    kite = KiteConnect(api_key=api_key)
    url = kite.login_url()
    r = requests.get(url=url)
    return f"<html><a href={r.url}><html>"



access_token = get_access_token()
kws = KiteTicker(api_key, access_token)
kite = KiteConnect(api_key = api_key)
kite.set_access_token(access_token)
db = TinyDB("current_trade.json")

temp = []
count_dt =0

def dump_data():
    global temp, count_dt
    if not os.path.isfile("current_trading_data222.csv"):
        df = DataFrame(temp)
        df.to_csv("current_trading_data222.csv", index=False)
        logging.info("df dumped of size:" + str(len(df)))
    else:
        df = read_csv("current_trading_data222.csv", on_bad_lines='skip')
        t= DataFrame(temp)
        t = t[df.columns]
        df = concat([df, t])
        df.to_csv("current_trading_data222.csv", index=False)
    count_dt = 0
    temp = []

def on_ticks(ws, ticks):
    global temp, count_dt
    tt = []
    for i in ticks:
        tt.append({
            "instrument_token": i["instrument_token"],
            "last_price": i["last_price"],
            "last_trade_time": i["last_trade_time"]
        })

    try:
        if count_dt == 500:
            t1 = threading.Thread(target=dump_data, args=())
            t1.start()
        else:
            temp = temp + tt
            count_dt += 1
        logging.debug("{} , Ticks: {}".format(count_dt, tt))
    except Exception as e:
        print("error", e)


def on_connect(ws, response):
    pass


def on_close(ws, code, reason):
    # On connection close stop the main loop
    # Reconnection will not happen after executing `ws.stop()`
    ws.stop()

# Assign the callbacks.
kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close


kws.connect(threaded=True)
count = 0
wait = 0

df = DataFrame(kite.instruments())


while True:
    try:
        if count < len(tokens):
            if kws.is_connected():
                kws.subscribe([tokens[count]])
                kws.set_mode(kws.MODE_FULL, [tokens[count]])
                count += 1
            else:
                wait += 1
                logging.info(f"Connecting to WebSocket.....")
    except Exception as e:
        print("error", e)



