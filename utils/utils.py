from kiteconnect import KiteConnect
from configs.config import api_key, api_secret, totp_secret, user_id,password
import pyotp
from selenium import webdriver
from selenium.webdriver.common.by import By
from pandas import DataFrame
from nsepython import *
from datetime import datetime, timedelta, date

logging.basicConfig(level=logging.DEBUG)


def candle_times():
    year = datetime.now().year
    month = datetime.now().month
    date = datetime.now().day
    def datetime_range(start, end, delta):
        current = start
        while current < end:
            yield current
            current += delta
    dt_ = [dt for dt in
           datetime_range(
               datetime(year, month, date, 9, 15),
               datetime(year, month, date, 15, 25),
               timedelta(minutes=5)
           )
    ]
    dts = [[dt_[i], dt_[i + 1]] for i in range(len(dt_) - 1)]
    c_time, c_data = {}, {}
    for k, v in enumerate(dts):
        c_time[k] = v
        c_data[k] = []
    return c_time, c_data, dt_


def get_access_token(
        api_key=api_key,
        user_id=user_id,
        password=password,
        totp_secret=totp_secret
):
    access_token = ""
    access_token_file = open('../configs/access_token.txt', 'r')
    token_info = access_token_file.readlines()
    print(datetime.utcnow())
    today_date = str(datetime.now().strftime("%Y-%m-%d") + "\n")
    if len(token_info) == 2 and token_info[0] == today_date:
        access_token = token_info[1]
        print("Today's Token already available: ", access_token)
        return access_token
    driver = webdriver.Chrome()
    kite = KiteConnect(api_key=api_key)
    url = kite.login_url()
    r = requests.get(url=url)
    driver.get(r.url)
    while 1:
        try:
            element = driver.find_element(By.ID, "userid")
            break
        except:
            pass
    element.send_keys(user_id)
    element = driver.find_element(By.ID, "password")
    element.send_keys(password)
    button = driver.find_element( By.CLASS_NAME, 'button-orange.wide')
    button.click()
    auth_key = pyotp.TOTP(totp_secret)
    current_key = auth_key.now()
    time.sleep(2)
    while 1:
        try:
            element = driver.find_element(
                By.XPATH,
                "//*[@id='container']/div[2]/div/div/form/div[1]/input"
            )
            break
        except: pass
    element.send_keys(current_key)
    while 1:
        try:
            button = driver.find_element(
                By.XPATH,
                "//*[@id='container']/div[2]/div/div/form/div[2]/button"
            )
            break
        except: pass
    button.click()
    r_url = driver.current_url
    for i in range(10):
        r_url=driver.current_url
        if "request_token" in r_url:
            break
        time.sleep(1)
    request_token = r_url.split("request_token=")[1].split("&")[0]
    data = kite.generate_session(request_token, api_secret=api_secret)
    access_token=data["access_token"]
    with open('../configs/access_token.txt', 'w') as f:
        f.write(str(datetime.now().strftime("%Y-%m-%d"))+"\n")
        f.write(access_token)


    print(access_token)
    return access_token


def instrument_token(api_key, exchange, instrument_name):
    kite = KiteConnect(api_key=api_key)
    print(kite.instruments(kite.EXCHANGE_NFO))
    instrument_info = kite.instruments(exchange)
    instrument_token_id = None
    for instrument in instrument_info:
        if instrument['tradingsymbol'] == instrument_name:
            instrument_token_id = instrument['instrument_token']
            print(f"Instrument token for {instrument_name}: {instrument_token_id}")
            break
    return instrument_token_id


def index_all_strik(index):
    """

    :param index: NIFTY, BANKNIFTY, FINNIFTY
    :return: list of strick prices
    """
    return nse_fno(index)



def nse_quote(symbol):
    symbol = nsesymbolpurify(symbol)
    if any(x in symbol for x in fnolist()):
        payload = nsefetch('https://www.nseindia.com/api/quote-derivative?symbol='+symbol)
    else:
        payload = nsefetch('https://www.nseindia.com/api/quote-equity?symbol='+symbol)
    print(payload)
    return payload


def index_ltp(index: str="BANKNIFTY"):
    return nse_quote_ltp(index)


def compiled_tickes():
    today = datetime.today()
    days_to_thursday = (3 - today.weekday()) % 7
    result = ""
    if days_to_thursday == 0:
        present_thursday = today
        present_year = str(present_thursday.year)[-2:]
        present_month = str(present_thursday.month)
        present_day = str(present_thursday.day)
        if len(present_day) == 1:
            present_day = '0' + present_day
        result = present_year + present_month + present_day
    else:
        present_thursday = today + timedelta(days=days_to_thursday)
        present_year = str(present_thursday.year)[-2:]
        present_month = str(present_thursday.month)
        present_day = str(present_thursday.day)
        if len(present_day) == 1:
            present_day = '0' + present_day
        result = present_year + present_month + present_day
    return result

def get_expiry():
    today = datetime.today()
    days_to_thursday = (3 - today.weekday()) % 7
    if days_to_thursday == 0:
        return today.strftime("%Y-%m-%d")
    return (today + timedelta(days=days_to_thursday)).strftime("%Y-%m-%d")


def instruments_token(
    index: str="BANKNIFTY",
    at_the_money=True,
    price_range=False,
    ce=True,
    pe=True,
    kite=None,
    expiry=None
):
    if kite is None:
        access_token = get_access_token()
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
    # Get instrument token for Bank Nifty options
    data = kite.instruments(kite.EXCHANGE_NFO)
    data = DataFrame(data)
    data = data[data['name'] == index]
    ce_pe = []
    if ce and pe: ce_pe = ["CE", "PE"]
    elif ce: ce_pe = ["CE"]
    else: ce_pe = ["PE"]
    data['strike'] = data['strike'].apply(int)
    data = data[data['instrument_type'].isin(ce_pe)]
    if expiry is None:
        expiry = get_expiry()
    temp = data[data['expiry'] == expiry]
    if len(temp) == 0:
        expiry = expiry[:-2] + str(int(expiry[-2:])-1)
        temp = data.copy()
        temp['expiry'] = temp['expiry'].apply(str)
        temp = temp[temp['expiry'] == expiry]
    data = temp
    if at_the_money:
        strike = int(float(index_ltp(index)))
        strike_ce = strike - strike % 100
        strike_pe = strike + (100 - strike % 100)
        data_ce = data[(data['strike'] == strike_ce) & (data['instrument_type'] == 'CE')]
        data_ce = data_ce[['instrument_token', 'tradingsymbol']]
        data_pe = data[(data['strike'] == strike_pe) & (data['instrument_type'] == 'PE')]
        data_pe = data_pe[['instrument_token', 'tradingsymbol']]
        data_ce = dict([tuple(data_ce.to_dict('records')[0].values())])
        data_pe = dict([tuple(data_pe.to_dict('records')[0].values())])
        return data_ce, data_pe

    if price_range is not None:
        data = data.sort_values(by='last_price', ascending=False).reset_index(drop=True)
        data_ce = data[data['instrument_type'] == 'CE']
        data_pe = data[data['instrument_type'] == 'PE']
        data_ce = data_ce[data_ce['last_price'] < price_range].head(1)
        data_pe = data_pe[data_pe['last_price'] < price_range].head(1)
        data_ce = data_ce[['instrument_token', 'tradingsymbol']]
        data_pe = data_pe[['instrument_token', 'tradingsymbol']]
        data_ce = dict([tuple(data_ce.to_dict('records')[0].values())])
        data_pe = dict([tuple(data_pe.to_dict('records')[0].values())])
        return data_ce, data_pe


