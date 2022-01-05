import asyncio
import time
import datetime
import sys

from ib_insync import *

PORT = 7497
CID = 3
ib = None

def mini_test(ib):
    try:
        contract = Forex("EURUSD")
        ib.qualifyContracts(contract)
        # order = MarketOrder("SELL", 1)
        # ib.whatIfOrder(contract, order)
    except:
        return False 
    return True


def pause_for_reset():
    now = datetime.datetime.now()
    if now.hour == 16:         
        mins_left = 60 - now.minute
        print("1600 Reset -- Sleeping for: ", mins_left, " mins")
        
        time.sleep(6 * 60) #SLEEP until 5pm, then restart...
    else:
        time.sleep(5) #Otherwise, sleep for 15.


def onDisconnect():
    global ib 
    print('DISCONNECT EVENT !! ')
    pause_for_reset()


def onConnect():
    global ib
    print("CONNECT EVENT !! ")


def onError(reqId, ErrorCode, errorString, contract):
    global ib 
    print(errorString, ErrorCode)
    if contract != None and ErrorCode == 201: 
        print('Rejection ? ')




#if __name__ == '__main__': 
if len(sys.argv) >= 1:
    CID = sys.argv[1]




ib = IB()

ib.disconnectedEvent += onDisconnect ## TRYING this...
ib.connectedEvent += onConnect 
ib.errorEvent += onError

ib.connect('127.0.0.1', PORT, CID)

retries = 0
last = time.time() 
while True:

    tst = mini_test(ib) ## ANY way to make this less of a pain in the ass? Less slow, less invovled?

    ## SQL Lookup
    ## ADD to OMS here
    ## MAYBE literally right this out right here...?  Add an onOrderStatus event for sent + filled, and done.

    if not tst or not ib.isConnected():
        try:
            retries += 1
            ib.disconnect()
            time.sleep(2)
            ib.connect('127.0.0.1', PORT, CID)
            time.sleep(2)
            print('Reconnect Attempt ', retries, ' --- Success: ', ib.isConnected())
            ## Extra safety? 
            if retries >= 10:
                CID += 1
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            continue

    
    if time.time() > last + 5:
        last = time.time()
        is_con = ib.isConnected()
        print(f'< IB -- {ib} -- conn: {is_con} -- ', time.strftime('%X'), ' >')
        


## ------------ THIS works fine in CommandLine (NOT in VSC?!)
## THIS is the production ready version... will retry connecting endlessly...