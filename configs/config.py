import configparser
import os
from datetime import datetime


tickets_ce = {14099202: "BANKNIFTY2331638400CE"}
tickets_pe = {14102530: "BANKNIFTY2331639000PE"}
tickets={14099202: "BANKNIFTY2331638400CE", 14102530: "BANKNIFTY2331639000PE"}
tokens_ce = list(tickets_ce.keys())
tokens_pe = list(tickets_pe.keys())
candle_duration = 5
sell_margin = 20
max_stop_loss = 2
stop_loss_trail_margin = 10
quantity=25

config = configparser.RawConfigParser()
config.read("{}/{}".format(os.path.join(os.path.dirname(__file__)), "config.ini"))
ENV = os.environ.get("FLASK_ENV", "dev")
status_file_path_ce = '/Users/mukul/PycharmProjects/AutomateTrading/data/current_trade_ce.json'
status_file_path_pe = '/Users/mukul/PycharmProjects/AutomateTrading/data/current_trade_pe.json'


api_key="gft6amzyywoorxa9"
api_secret="70ik8sezbdeg618bkwz440yp4v8yrs5j"
totp_secret="DBJ3X7IMZ5UEKSSW4A7AISF7HK46CRWS"
user_id="PDC829"
password="mukul@123"









