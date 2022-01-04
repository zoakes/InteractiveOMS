

# -*- coding: utf-8 -*-
"""
Created on Tue Oct  5 16:29:01 2021

@author: zach
"""

from cfg_ib import root_to_front, root_qty, root_exch_ib

from ib_insync import *
from ibapi import *
import time
import sys

import asyncio

import random 

ib = None
PORT = 7497
CID = random.randint(1,9900)

SYMBOL = 'QQQ' # 'EURUSD' # ## FOR TESTING only --------- THIS needs to be from a cfg
USING_NOTEBOOK = True # IF using Spyder...

if USING_NOTEBOOK:
    util.startLoop()
    

## ---------------- Example (Futures Symbol) ------------------ ## 
    
# fut_contract = Contract()
# fut_contract.secType = 'FUT'
# fut_contract.exchange = 'GLOBEX'
# fut_contract.currency = 'USD'
# fut_contract.symbol = 'MNQ'
# fut_contract.localSymbol = 'MNQH2'
# ib.qualifyContracts(fut_contract)
    
## ------------------------ Handlers ---------------------- ##
    
def onExecDetails(trade, fill):
    #trade.orderStatus.status == 'Fill' or 'Filled'
    symbol = trade.contract.localSymbol
    status = trade.orderStatus.status
    tm = time.strftime('%X')
    
    print(f"\nUpdated Order Status --  ({symbol}) : {status}\n")
    
    if status in ['Submitted', 'PreSubmitted', 'PendingSubmit']:
        print(f'{tm} Order Submitted -- {symbol}')
        
        ## ---------- WRITE to Database (SENT)
    
    if status in ['Filled', 'Fill', 'fill', 'filled']:
        print(f'{tm} Order Filled -- {symbol}')
        
        ## ---------- WRITE to Database (FILLED )
        
    if status in ['Cancelled','PendingCancel']:
        print(f'{tm} Order Cancelled -- {symbol}')
        
        
    # try:
    #     if ibc:
    #         ib_id = trade.order.orderId
            
    #         # sql_uid = trade. UNSURE how to get this here...
    #         ibc.filled.append(ib_id)
        
'''
I think to make this completely synced, with BOTH UIDs, could either match them, or add a column.
To record the UIDs as they are sent (BOTH uid, and ibs orderId) or filled, think it would need to be monolith or close.

'''

class IBClient:
    
    
    def __init__(self, port=7497, cid=CID):
        self.ib = IB()
        self.port = port
        self.cid = cid ## COULD generate here...
        self.rt_ct = 0
        
        self.stps = []
        
        self.connect_to_ib() #Added into here... 
        
        time.sleep(1)
        
        self.stps = []
        self.last = None
        
        # Doesnt work here... dont know why.
        # bars = self.ib.reqRealTimeBars(self.contract, 5, 'MIDPOINT', False)
        # bars.updateEvent += self.onBarUpdate
        
        ## Subscribe to order Events
        self.ib.execDetailsEvent += onExecDetails
        self.filled = []
        
        #Keep it an instance method ----- NOT needed + also like I can pass this in later.
        
        # self.ib.execDetailsEvent += self.onExecDetailsClass                     #THIS works if you want to update self.filled... 
        # self.filled = []                        # POPULATE THIS with FILLED list. ?? 
        
        self.qualified_local_symbols = []
        
        
    

    def connect_to_ib(self):
        #self.cid += 1 #NOT sure if this will work here? 
        print('Connecting to ib...')
        try:
            self.ib.connect('127.0.0.1', self.port, self.cid)
        except:
            #Recurse...
            self.rt_ct += 1
            self.cid += 1 
            if self.rt_ct < 5:
                self.connect_to_ib()
            else:
                print('Could not connect... exitting.')
                sys.exit(-1)
                
        print('Success.')
        
        
    def get_front_contract(self, root, qualify=True):
        front = root_to_front[root]
        exch = root_exch_ib[root]
        
        contract = Contract()
        contract.secType = 'FUT'
        contract.exchange = exch
        contract.currency = 'USD'
        contract.symbol = root
        contract.localSymbol = front
        
        if qualify and front not in self.qualified_local_symbols:
            self.ib.qualifyContracts(contract)
            
            self.qualified_local_symbols.append(contract.localSymbol)
            print(f'Cached {contract.localSymbol} (Wont qualify unless diff front)')
        
        return contract
    
    
    
        
    def send_stop_order(self, symbol, side, qty, offset):
        if not self.is_connected:
            self.connect_to_ib()

        try:
            price = self.get_last_close() + offset    #USE NEGATIVE or POS offsets for above below.
        except:
            #MOCKED 
            print('MOCKING the stop price (no data).')
            price = 300 if 'b' in side else 500
            
        price = round(price,2)
            
        contract = self.get_front_contract(symbol, True)
        
        action = 'BUY' if 'b' in side else 'SELL'
        order = StopOrder(action, qty, price)
        
        self.stps.append(order)
        
        symbol = contract.localSymbol
        
        trade = self.ib.placeOrder(contract, order)
        print(f'Stop Order Sent -- {symbol} - {action} @ {price} x {qty}')
        
        
        
    def send_order(self, symbol, side, qty):
        if not self.is_connected:
            self.connect_to_ib()
            #Sleep?
        

        contract = self.get_front_contract(symbol, True)
        
        action = 'BUY' if 'b' in side.lower() else 'SELL'             #MODIFIED THIS !! (from 'buy in side' to b in side)
        order = MarketOrder(action, qty)
        
        trade = self.ib.placeOrder(contract, order)
        symbol = contract.localSymbol
        print(f'Order Sent -- {symbol} - {action} x {qty} --- {trade.orderStatus}')
        
        if trade in self.ib.trades():
            print(f'Success -- {symbol} {trade.orderStatus.status}')
            return 1, trade
        return -1, trade
    
    
    def send_limit_order(self, symbol, side, qty, price):
        contract = self.get_front_contract(symbol, True)
        
        action = 'BUY' if 'b' in side.lower() else 'SELL'
        order = LimitOrder(action, qty, price)
        trade = self.ib.placeOrder(contract, order)
        print(f'Order Sent -- {symbol} - {action} x {qty} --- {trade.orderStatus}')
        
        ## WRITE to database (or wait for event handler?)
        if trade.orderStatus.status in ['PendingSubmit', 'Submitted', 'PreSubmitted']:
            print('Success.')
            return 1, trade
        return -1
    
        
    def market_order_with_fill(self, symbol, side, qty):
        """
        BLOCKING wait for fill (Not ideal, use events instead!)
        """
        if not self.is_connected:
            self.connect_to_ib()
        
        
        action = "BUY" if 'b' in side.lower() else 'SELL'
        order = MarketOrder(action, qty)
        
        ## MATCH contract with cgf of symbols + qualify it.
        contract = self.get_front_contract(symbol, True)
        
        
        trade = self.ib.placeOrder(contract, order)
        
        ## ---------------------------------- BLOCKING (wait for fill) -------------- ## 
        while not trade.isDone():
            self.ib.waitOnUpdate()
        
        return 1, trade
        
        
    def flatten(self, symbol):
        qty = self.current_quantity
        # Place market order to go flat

        if qty > 0:
            action = 'sell'
        elif qty < 0:
            action = 'buy'
        else:
            print(f'{symbol} already FLAT.')
            return
        
        # print('----------- QUANTITY ------------', qty)
        # print('----------- Respective CLOSE order', action)
        # Place market order to go flat
        #self.market_order(instrument, action, abs(qty))
        self.send_order(symbol, action, abs(qty))
        
    # There is a Builtin --- self.ib.isConnected()  (No need for this)
    @property
    def is_connected(self):
        #'connected' in str(ib)
        return 'connected' in str(self.ib) and f'clientId={self.cid}' in str(self.ib)
    
    
    # @property
    # def current_quantity(self):
    #     #Uses GLOBAL symbol... (COULD be a non prop, and accept symbol argument...)
    #     for position in self.ib.positions():
    #         contract = position.contract
    #         if contract.localSymbol == SYMBOL:
    #             print('Active Position: (This can be delayed)', position.position)
    #             time.sleep(1)
    #             return int(position.position)
    #     return 0
    
    # -------------- Other Helpers ---------------- ## 
    
    def assert_trade_active(self, trade):
        return trade.orderStatus.status in ['Submitted', 'Filled'] or trade in self.ib.trades()
        
    #NOT using global...
    def get_symbol_quantity(self, symbol):
        for pos in self.ib.positions():
            contract = pos.contract
            if contract.localSymbol == symbol:
                print(pos.position, int(pos.position))
                time.sleep(1)
                return int(pos.position)
        return 0
    
    ## BINGO --- THIS works. (SLOW -- but it works.)
    def cancel_pending_orders(self):
        active_uids = [i.order.orderId for i in self.ib.trades() if i.isActive()]
        #cancel_orders = [ib.cancelOrder(i) for i in ib.orders() if i.orderId in active_uids]
        for order in self.ib.orders():
            if order.orderId in active_uids and order.orderType == 'STP':     # ADDIT 
                self.ib.cancelOrder(order)
                print(f'Cancelled Order -- {order}')
                
    # def cancel_stop_orders(self):
    #     for order in self.ib.orders():
    #         if order.orderType == "STP":
    #             self.ib.cancelOrder(order)
    #             print(f'Cancelled Order -- {order}')
                
    #Slow. but reliable.
    def get_last_close(self):
        bars = self.ib.reqHistoricalData(
            self.contract,
            endDateTime='',
            durationStr='900 S',
            barSizeSetting='10 secs',
            whatToShow='MIDPOINT',
            useRTH=True,
            formatDate=1,
            keepUpToDate=True)
        

        if len(bars) > 0:
            self.last = bars[-1].close
            return self.last
    
    
    #Should work -- doesnt for some fucking reason.
    def get_snapshot(self):
        t = self.ib.reqMktData(self.contract,'',True, False).marketPrice()

        return t
    
    #Unreliable
    def get_last_fill_price(self):
        last_trade = self.ib.trades()[-1]
        if last_trade:
            return last_trade.orderStatus.avgFillPrice
        
        
    #Doesnt fucking work either.
    def onBarUpdate(self, bars, hasNewBar):
        last_bar = bars[-1]
        if last_bar:
            self.last = last_bar.close
        
        
    def onExecDetailsClass(self, trade, fill):
        #trade.orderStatus.status == 'Fill' or 'Filled'
        symbol = trade.contract.localSymbol
        status = trade.orderStatus.status
        tm = time.strftime('%X')
        
        print(f"\nUpdated Order Status --  ({symbol}) : {status}\n")
        
        if status in ['Submitted', 'PreSubmitted', 'PendingSubmit']:
            print(f'{tm} Order Submitted -- {symbol}')
            
            ## ---------- WRITE to Databse (SENT)
        
        if status in ['Filled', 'Fill', 'fill', 'filled']:
            print(f'{tm} Order Filled -- {symbol}')
            
            ## ---------- WRITE to Database (FILLED )
            
        if status in ['Cancelled','PendingCancel']:
            print(f'{tm} Order Cancelled -- {symbol}')
        
    
    


        

            
            
if __name__ == '__main__':
    
    # SYMBOL = 'EURUSD' #Testing only.
    
    ibc = IBClient(7497) #IF not set here, will use Random CID (better)
    #ibc.connect_to_ib()
    res = ibc.get_front_contract('ES',True)
    
    print(res)
    
    # Works...  (Add to test case later...)
    # res = ibc.get_front_contract('ES',True) #Make sure it doesn't qualify again...
    
    ## --------------- Test Orders + Events : ) --------------------------- ##
    
    ibc.send_order('MES','BUY',1)
    ibc.send_order('MES','SELL',1)
    
    ibc.send_order('MNQ','BUY',1)
    ibc.send_order('MNQ','SELL',1)
    
    ibc.ib.sleep(5)
    
    # WHY is it showing positions still ? 
    # ibc.flatten()
    # print(ibc.ib.positions())

    

    

    
    


    
    
    
    