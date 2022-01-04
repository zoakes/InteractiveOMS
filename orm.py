# -*- coding: utf-8 -*-
"""
Created on Mon Jan  3 12:25:57 2022

@author: zach
"""
import mysql.connector
import time
import datetime

import asyncio

# ---------------------------------------- SQL METHODS --------------------------------------------------- ##


cnx = None
cur = None


    
async def sql_init():
    global cnx
    global cur

    ## ---------------------------- ABSTRACT to CGF later !!! 
    cnx = mysql.connector.connect(user='zach', password='zoakes1290',
                                  host = '192.168.1.178',
                                  database='test',
                                  auth_plugin='mysql_native_password',
                                  autocommit=True)
    cur = cnx.cursor(buffered=True)


async def read_sql_detail(sent=False, filled=False):
    global cur
    global cnx
    
    cur.execute(f"SELECT * FROM oms WHERE sent = {int(sent)} AND filled = {int(filled)}")
    return cur.fetchall()


async def read_sql():
    # SAVEd credentials (MOVE to config)
    # https://stackoverflow.com/questions/9305669/mysql-python-connection-does-not-see-changes-to-database-made-on-another-connect
    global cnx
    global cur

    if cnx is None or cur is None:
        await sql_init()

    cur.execute("SELECT * FROM oms WHERE sent = 0")                                                                     # SET THIS IN CFG_?
    results = cur.fetchall()
    return results



def sql_update_sent(uid):
    global cnx
    global cur

    sql = f"UPDATE oms SET sent = 1 WHERE uid = {uid}"  # ?"  # (%s)"
    cur.execute(sql)
    cnx.commit()
    
def sql_update_filled(uid):
    global cnx
    global cur
    
    sql = f"UPDATE oms SET filled = 1 WHERE uid = {uid}"
    cur.execute(sql)
    cnx.commit()


#Needs to MATCH filled by details...
def sql_match_update_filled(symbol, side, qty):
    """
    Since it doesnt matter WHICH order is filled (in case of 2x identical MKT orders)...
    WHY not simply report the FIRST one (not filled) as FILLED.

    :param symbol: Symbol filled (root or front?), STR
    :param side: 1 or -1, INT
    :param qty: 1 - 100, INT
    :return: None
    """

    global cnx
    global cur
    global filled
    #global last_uid    # Maybe this is better ?

    try:
        root = symbol[0:2] # ENSURE this uses ROOT and not SYMBOL here !!
        sent_not_filled = [i for i in sent if i not in filled]
        approx_uid = [i[0] for i in sent_not_filled if i[1] == root and i[2] == side and i[3] == qty]

        sql = f"UPDATE oms SET filled = 1 WHERE uid = {approx_uid}"

        cur.execute(sql)
        cnx.commit()
        print(f'Order Filled {root, side, qty}')
        return 1
    except Exception as e:
        print("Failed fill update-- ", e)
        return -1


# def sql_update_filled(ib_uid):
#     global cnx
#     global cur
#     global filled #THIS wont work as well
    
#     sql = f'UPDATE oms SET filled = 1 WHERE '
    



## ---------------------------------------------- OMS Methods ---------------------------------------------- ##


## VERY rough...
orders = []
sent = []
filled = []
last_uid = None

async def add_to_oms(ws, new):
    ## Accepts a LIST (of ORDERS -- lists)
    global orders
    global sent
    global last_uid

    not_sent = [i for i in new if i not in sent]

    print("New Trades: ", len(not_sent))

    for order in not_sent:
        # Add to ORDERS list (ALL orders in here)
        orders += [order]

        uid, symbol, side, qty, *rem = order
        # await send_order(ws, symbol, int(side), int(qty))          ## UNCOMMENT TO ACTUALLY EXECUTE !! (Need to update database first -- include UID?)

        sql_update_sent(uid)

        # Add to SENT list.
        sent += [order]
        last_uid = uid
        print('Order Sent: ', order)


    await asyncio.sleep(1)      # MOCK SQL add -- REMOVE this