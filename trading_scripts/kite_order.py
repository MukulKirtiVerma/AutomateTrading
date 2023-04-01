def zerodha_place_order(kite, trading_symbol, quantity, buy_at, stop_loss, target_order):
    global order_id
    order_id = kite.place_order(
        tradingsymbol=trading_symbol,
        exchange='NSE',
        transaction_type='BUY',
        quantity=quantity,
        product='MIS',
        variety='regular',
        order_type='LIMIT',
        price=buy_at
    )

    # Stop Loss
    sl_order_id = kite.place_order(
        tradingsymbol=trading_symbol,
       exchange='NSE',
       transaction_type='SELL',
       quantity=quantity,
       product='MIS',
       variety='regular',
       order_type='SL',
       trigger_price=stop_loss,
       stoploss=stop_loss
    )

    # target_order
    exit_order_id = kite.place_order(
        tradingsymbol=trading_symbol,
        exchange='NSE',
        transaction_type='BUY',
        quantity=1,
        product='MIS',
        variety='regular',
        order_type='LIMIT',
        price=298.4
    )

def zerodha_update_order(kite, new_stoploss):
    global  order_id
    kite.modify_order(
        order_id=order_id,
        price=new_stoploss,
        trigger_price=new_stoploss
    )

