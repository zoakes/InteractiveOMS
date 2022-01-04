import asyncio
import time
import datetime

from ib_insync import IB

PORT = 7497
CID = 2


def pause_for_reset():
    now = datetime.datetime.now()
    if now.hour == 16:         
        mins_left = 60 - now.minute
        print(mins_left)
        
        time.sleep(6 * 60) #SLEEP until 5pm, then restart...
    else:
        time.sleep(15) #Otherwise, sleep for 15.

# -------- Initial Connection ---------- ## 

ib = IB()

if not ib.isConnected():
    ib.connect('127.0.0.1',PORT, CID)
    
## ----------- Long Lived Connection ------------- ## 


last = time.time()
while True:
    
    # while not ib.isConnected(): #THIS is a more perpetual version
    if not ib.isConnected():
        # ib.disconnect()
        # ib.sleep(10)

        ## --------- Begin Addit 
        #if datetime.datetime.now().hour == 16:
        #Disconnect EACH time youre unsure, pause for a bit (or a while if 1600), retry.
        ib.disconnect()

        pause_for_reset()
        ## --------- Emd Addit 

        ib.connect('127.0.0.1', PORT, CID)
        print('Reconnected -- ', ib.isConnected())
    
    ## Normal operation 
    if time.time() > last + 5:
        last = time.time()
        print(f'< IB -- {ib} -- ', time.strftime('%X'), ' >')
