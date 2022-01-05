# -*- coding: utf-8 -*-
"""
Created on Mon Jan  3 12:20:34 2022

@author: zach
"""


import asyncio
from IBC import IBClient, PORT, CID

from orm import * #Sloppy, clean up later.

from Order import Order

import sys
import datetime
import time

g_sql_task = None
g_kill = False

## ---------------------- Handler ------------------------ ## 

'''
THIS could truly be treated like a callback + passed to IBC as an argument : )
## OR even better, SUBSCRIBED to ibc as an argument... 


def onExecDetails(trade, fill):
    #trade.orderStatus.status == 'Fill' or 'Filled'
    symbol = trade.contract.localSymbol
    status = trade.orderStatus.status
    tm = time.strftime('%X')
    
    print(f"\nUpdated Order Status --  ({symbol}) : {status}\n")
    
    # DO whatever here...
        
'''

class IBB:
    
    
    def __init__(self, ibc):
        self.ibc = ibc
        
        self.orders = []
        self.sent = []
        self.filled = []
        
        ## --------------------- Makes sense to save both, bc we WONT have a orderId prior to sending order. CANT force them to be the same, always awkward...
        ## NOT needed for markets, but for limits later, will be helpful to have BOTH values saved. 
        ## (Will remove excess bs when finished.)
        
        self.filled_uids = []
        self.filled_oids = []
        #self.last_uid = None
        
        self.orderId_by_uid = {}
        self.orders_by_uid = {}
        
        
        '''
        -----------------  CAN ALSO SUBSCRIBE TO EVENTS HERE !!!   -----------------
        say self.ibc.ib.execDetailsEvent += OnExecDetails 
        
        ib = self.ibc.ib
        ib.orderStatusEvent += onOrderStatus 
        
        '''
        
        ib = self.ibc.ib
        ib.orderStatusEvent += self.onOrderStatusUpdate
        
        ib.disconnectedEvent += self.onDisconnect
        
        ## Trades has order, orderStatus, contract, log, fills -- anything we would need.
        
        self.filled_trades = []
        self.sent_trades = []
        
    
        
    def onDisconnect(self):
        print('Disconnect Event')
        IBB.pause_for_reset()
        
        
    
    ## THIS definitely gives us FILLED EVENT, and PRE SUBMITTED ! BOTH are sufficient. (filled, sent)
    def onOrderStatusUpdate(self, trade):
        status = trade.orderStatus.status
        orderId = trade.orderStatus.orderId
        direction = trade.order.action
        qty = trade.order.totalQuantity
        fill_price = trade.orderStatus.avgFillPrice
        symbol = trade.contract.localSymbol
        
        if orderId != 0:
            uid = [k for k, v in self.orderId_by_uid.items() if v == oid]
        
        
        print("status:      ", status)
        print("symbol:      ", symbol)
        print(f'ID:           {orderId}')
        print(f'dir:          {direction}')
        print(f'qty:          {qty}')
        print(f'fill price:   {fill_price}')
        
        if status == 'Filled':
            self.filled_trades += [trade]
            self.filled_oids += [oid]
            
            self.filled += [uid]
            
            # Update Sql table w filled (Fully done -- useful for limits)
            sql_update_filled(uid)
        
        if status in ['Submitted', 'PreSubmitted']:
            self.sent_trades += [trade]
            
            # Maybe not even needed...
            if uid not in self.sent:
                self.sent += [uid]
            
        if 'Cancelled' in status:
            print("Order Cancelled -- ALERT VIA EMAIL REJECTION?")
            
            
        
    async def robust_run(self):
        """
        THIS handles RECONNECT WITH SAME CID !! 
        (To try NEW CID reconnection, try using OTHER RUN METHODS -- inf_order_read_and_send() or run() )
        
        if not connected, disconnects, pauses, reconnects to SAME CID
            Retries up to 5 times.
        IF connected, reads for new sql orders. 
        
        
        Returns out when killed (with global, g_kill)
        -------
        """
        global g_kill 
        
        # ib = self.ibc.ib
        # if not ib.isConnected():
        #     # THIS needs to match ALL others! (via Global)
        #     self.ibc.ib.connect('127.0.0.1', PORT, CID) 
        
        ct = 0
        
        last = time.time()
        while True:
            
            tst = self.ibc.noop()
            
            if not self.ibc.ib.isConnected() or not tst:
                
                try:
                    retries += 1
                    self.ibc.ib.disconnect() 
                    time.sleep(2)
                    self.ibc.ib.connect('127.0.0.1', PORT, CID)
                    time.sleep(2)
                    print(f'Reconnect Attempt {retries} --- Success: ', self.ibc.ib.isConnected())
                except KeyboardInterrupt:
                    sys.exit()
                except Exception as e:
                    continue #Try again
                    
            
            ## IS Connected 
            
            res = await read_sql()
            if len(res) > 0:
                self.add_to_oms(res)
        
            if time.time() > last + 5:
                last = time.time()
                print(f'< IB -- {ib} -- ', time.strftime('%X'),' >')
                
            
            if g_kill:
                print('Exitting Program....')
                return
        
            
    # Non Blocking run
    async def run(self):
        ## NON Blocking run call (Not needed)
        # asyncio.create_task()
        global g_sql_task
        self.inf_task = asyncio.create_task( self.inf_order_read_and_send() )
        
        
    # Blocking run call (Sufficient)
    async def inf_order_read_and_send(self):
        """
        READ AND SEND LOOP ! 
        (UPDATE as SENT)
        
        Infinite runtime, loop through + read new orders from sql
        IF new orders, add to OMS -> Send + update as sent (in sql, and locally)
        
        READS new orders (from bridge via sql)
        
        DELEGATES new orders to be sent (add_to_oms)
        DELEGATES new WRITES (to sql, add to oms)
        
        """
        global g_kill


        last = time.time()
        while True:
            t1 = time.time_ns()
            res = await read_sql() #From ORM 
            
            # IF new orders present, ADD to oms (simple oms, local lists + sql)
            if len(res) > 0:
                #await self.add_to_oms(res)
                self.add_to_oms(res)
            
            t2 = time.time_ns()
            
            #if len(res) == 0: await asyncio.sleep(.25) #Slow things down if empty...
    
    
            if time.time() > last + 5:
                print(f'< sql read  --  ', time.strftime('%X'), f' latency  --  {(t2 - t1)/1000}us', '>')
                last = time.time()
                
            if g_kill: return
                
                
    # Send new orders + record as sent in sql
    def add_to_oms(self, new):
        """
        Read through new orders, confirm unsent.
        add to orders (ALL orders list)
        
        Send order, and update as sent.
        (Also save ib id and uids in a dict, so can be matched later if needed -- like in onExecDetails! )
        """
        
        unsent =  [i for i in new if i not in self.sent]
        
        print("New Trades: ", len(not_sent))
        
        # ADD to orders
        for order in unsent:
            #Save all orders (sql row orders)
            self.orders += [order] 
            
            # Unpack details
            uid, symbol, side, qty, *rem = order
            
            side = 'b' if side > 0 else 's'
            res, trade = self.ibc.send_order(symbol, side, abs(int(qty)))               # ibc.send_order('MES','BUY',1)
            
            # Update that it was sent (OR let that happen in handler?) CAN add event handler HERE in init?
            if res != -1:
                self.sent += [order]
                sql_update_sent(uid)                                            # From ORM  (COULD also do this in OnExecDetails -- Submitted)
                ## COULD also save the ib_id here !! 
                ib_id = trade.order.orderId
                
                self.orderIds_by_uid[uid] = ib_id
                self.orders_by_uid[uid] = trade
                
                ## THIS would be the time to save it as a dataclass, with BOTH items !! 
            
            print('Order Sent: ', order)
        
    
    
    @staticmethod
    def pause_for_reset(reset_hr = 16):
        now = datetime.datetime.now()
        if now.hour == reset_hr:
            mins_left = 60 - now.minute
            print(f'{reset_hr}:00 reset -- Sleeping for: {mins_left} mins...')
            time.sleep(60 * mins_left)
        else:
            time.sleep(5) #Otherwise, sleep for 5 seconds.
    
    ## ------------------------- Helpers ------------------------------ ## 
            
    # NOT needed with orderStatusEvent : )
            
    def check_ib_filled_orders(self):
        """
        Check which orders have filled (According to IB)
        Returns tuple of lists:
            FILLED OIDS (orderIds), FILLED UIDS (sql indexes)
        """
                        
        filled_orderIds = [i.order.orderId for i in self.ibc.trades() \
                               if i.order.orderId != 0 \
                               and i.orderStatus.status == 'Filled']
        
        filled_uids = [k for k,v in self.orderIds_by_uid.items() if v in filled_orderIds]
        
        
        #self.filled_oids = list(set(self.filled_oids.append(filled_orderIds)))
        #self.filled_uids = list(set(self.filled_uids.append(filled_uids)))
        
        newly_filled_oids = []
        for oid in filled_orderIds:
            if oid not in self.filled_oids:
                self.filled_oids += [oid]
                newly_filled_oids += [oid]
                
        newly_filled_uids = []
        for uid in filled_uids:
            if uid not in self.filled_uids:
                self.filled_uids += [uid]
                newly_filled_uids += [uid]
                
        return self.filled_oids, self.filled_uids
        

    # Dont think I need this, given I will haev stream of statuses
    def check_sql_update_filled(self):
        '''
        Lookup in sql which are filled...
        '''
        rows = read_sql_detail(True, True)
        filled_uids = [i[0] for i in rows]
        return filled_uids
          
        
                    
        
    async def kill_sql_task(self):
        from contextlib import suppress
        #https://stackoverflow.com/questions/44982332/asyncio-await-and-infinite-loops

    
        #task = g_sql_task
        task = self.task
    
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task  # await for task cancellation


            
    
if __name__ == '__main__':
    
    import random 
    
    
    ## ------------------------ TESTING LINE ONLY (Makes it less reliable client live) ----------------- ## 
    CID = random.randint(1,9900) 
    #TO randomize -- you WILL lose pending orders this way though... ( ---------- WARNING --------- )


    ibc = IBClient(PORT,CID)      
    print(ibc)  
    
    ibb = IBB(ibc)
    
    try:
        # Blocking Version...
        asyncio.run(ibb.inf_order_read_and_send())
        
        # BEST version ... 
        #asyncio.run(ibb.robust_run()) ## Untested ! but more robust...
        
        ## NON Blocking version... 
        #asyncio.run(ibb.run() )
    except:
        try:
            if ibb.inf_task:
                ibb.kill_sql_task()
        except:
            pass
        
        g_kill = True
        
        time.sleep(1)
        sys.exit(1)
            
