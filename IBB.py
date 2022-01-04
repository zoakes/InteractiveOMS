# -*- coding: utf-8 -*-
"""
Created on Mon Jan  3 12:20:34 2022

@author: zach
"""


import asyncio
from IBC import IBClient

from orm import * #Sloppy, clean up later.


import datetime
import time

g_sql_task = None
g_kill = False

## ---------------------- Handler ------------------------ ## 

'''
THIS could truly be treated like a callback + passed to IBC as an argument : )


def onExecDetails(trade, fill):
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
        
'''

class IBB:
    
    
    def __init__(self, ibc):
        self.ibc = ibc
        
        self.orders = []
        self.sent = []
        self.filled = []
        
        self.filled_uids = []
        self.filled_oids = []
        #self.last_uid = None
        
        self.orderId_by_uid = {}
        self.orders_by_uid = {}
        
        
        '''
        CAN ALSO SUBSCRIBE TO EVENTS HERE !!!  ------------------------------------------------------- ************
        say self.ibc.ib.execDetailsEvent += OnExecDetails 
        
        '''
        
    
    async def run(self):
        # asyncio.create_task()
        global g_sql_task
        self.inf_task = asyncio.create_task( self.inf_sql_loop() )
        
        
        
    async def inf_sql_loop(self):
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
        
        sql_read_ct = 0

        last = time.time()
        while True:
            t1 = time.time_ns()
            res = await read_sql() #From ORM 
            t2 = time.time_ns()
    
            # IF new orders present, ADD to oms (simple oms, local lists + sql)
            if len(res) > 0:
                #await self.add_to_oms(res)
                self.add_to_oms(res)
    
            if len(res) == 0: await asyncio.sleep(.25)             # TEMP !! (to SLOW things down with small database)
    
            # print(f'Testing Inf Sql Read --- New Trades: {len(res)} Count: {sql_read_ct}')
            sql_read_ct += 1
    
            if time.time() > last + 5:
                print(f'< sql read  --  ', time.strftime('%X'), f' latency  --  {(t2 - t1)/1000}us', '>')
                last = time.time()
                
            if g_kill: return
                
                
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
            self.orders += [order]
            
            uid, symbol, side, qty, *rem = order
            
            side = 'b' if side > 0 else 's'
            res, trade = self.ibc.send_order(symbol, side, qty)                             # ibc.send_order('MES','BUY',1)
            
            # Update that it was sent (OR let that happen in handler?)
            if res != -1:
                self.sent += [order]
                sql_update_sent(uid)    # From ORM  (COULD also do this in OnExecDetails -- Submitted)
                ## COULD also save the ib_id here !! 
                ib_id = trade.order.orderId
                
                self.orderIds_by_uid[uid] = ib_id
                self.orders_by_uid[uid] = trade
                
                ## THIS would be the time to save it as a dataclass, with BOTH items !! 
            
            print('Order Sent: ', order)
        
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
    import sys
    
    # WHEN NOT TESTING -- replace with 
    CID = random.randint(1,9900) #TO randomize -- you WILL lose pending orders this way though...
    
    ## IBC Helper (TRUE IBC Commander) 
    # IBC(twsVersion=7497, gateway=False, tradingMode='', twsPath='', twsSettingsPath='', ibcPath='C:\\IBC', ibcIni='', javaPath='', userid='', password='', fixuserid='', fixpassword='')
    ibc = IBClient(7497,random.randint(1,9900))      
    print(ibc)  
    
    ibb = IBB(ibc)
    
    try:
        # Blocking Version...
        asyncio.run(ibb.inf_sql_loop())
        
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
            
