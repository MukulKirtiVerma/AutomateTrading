import json

from mega import Mega
from pandas import DataFrame, read_json

def megaa():
    mega = Mega()
    m = mega.login("mukulkirtiverma@gmail.com", "mukul@123A")
    folder = m.find('access_token')

    data = DataFrame({"last_update": ["2023-02-18"], "access_token": ["aJeGdmx6tfzJppPAczLPLwAojW8rVnxT"]})
    data.to_json('access_token.json')
    file = m.upload('access_token.json')
    m.get_upload_link(file)

# file = m.find('access_token.json')
#
# m.download(file)
#
# print(read_json('access_token.json').head())

def get_access_token_from_mega():
    mega = Mega()
    m = mega.login("mukulkirtiverma@gmail.com", "mukul@123A")
    folder = m.find('access_token')
    file = m.find('access_token.json')
    if file is None:
        return None
    m.download(file)
    data = read_json('access_token.json')
    access_token = data.iloc[0]['last_update']
    return m.get_upload_link(file)

# import kiteconnect
# import configparser
#
# # Load API credentials from config file
#
# kite = kiteconnect.KiteConnect(api_key="gft6amzyywoorxa9")
# kite.set_access_token("mtdt0ZqkI1V4VMDN2WtMHphIIUwDyFe6")
# g= kite.get_gtts()
# print(g)

# # Define the GTT order parameters
# order_params = {
#     "tradingsymbol": "BANKNIFTY2330240300CE",
#     "exchange": kite.EXCHANGE_NFO,
#     "trigger_type": "two-leg",
#     "trigger_values": [430, 488],
#     "last_price": 432,
#     "orders": [
#         {
#             "transaction_type": kite.TRANSACTION_TYPE_SELL,
#             "quantity": 25,
#             "order_type": kite.ORDER_TYPE_SL,
#             "product": "MIS",
#             "price": 430
#         },
#         {
#             "transaction_type": kite.TRANSACTION_TYPE_SELL,
#             "quantity": 25,
#             "order_type": "LIMIT",
#             "product": "MIS",
#             "price": 488
#         }
#     ],
# }
#
# # Place the GTT order
# response = kite.place_gtt(**order_params)
# print(response)
#
# new_order_params = {
#     "trigger_type": "two-leg",
#     "tradingsymbol": "BANKNIFTY2330240300CE",
#     "exchange": kite.EXCHANGE_NFO,
#     "trigger_values": [430, 488],
#     "last_price": 447,
#
#     "orders": [
#         {
#             "transaction_type": kite.TRANSACTION_TYPE_SELL,
#             "quantity": 25,
#             "order_type": kite.ORDER_TYPE_SL,
#             "product": "MIS",
#             "price": 430
#         },
#         {
#             "transaction_type": kite.TRANSACTION_TYPE_SELL,
#             "quantity": 25,
#             "order_type": "LIMIT",
#             "product": "MIS",
#             "price": 488
#         }
#     ]
# }
#
# # Modify the GTT order
# response = kite.modify_gtt(140837313, **new_order_params)
# print(response)
#


