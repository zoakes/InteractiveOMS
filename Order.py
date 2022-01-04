# -*- coding: utf-8 -*-
"""
Created on Mon Jan  3 20:09:16 2022

@author: zach
"""


from dataclasses import dataclass
import datetime

@dataclass
class Order:
    uid: int
    root: str
    side: int 
    qty: int

    oid: int = None
    symbol: str = None
    sent: bool = False
    filled: bool = False
    submitted_at: datetime.datetime = datetime.datetime.now()
    last_updated_at: datetime.datetime = datetime.datetime.now()
    
    
    def __init__(self, uid, root, side, qty, sent=False, filled=False, oid=None, symbol=None, submitted_at=datetime.datetime.now(), last_updated_at=datetime.datetime.now()):
        self.uid = uid
        self.root = root
        self.side = side
        self.qty = qty
        self.sent = sent 
        self.filled = filled 
        self.submitted_at = submitted_at
        self.last_updated_at = last_updated_at 
        
        
if __name__ == '__main__':
     
    test_order = Order(1,  'ES', 1, 1)
    
    
    t = test_order
    assert t.uid == 1
    assert t.root == 'ES'
    assert t.side == 1
    assert t.qty == 1
    assert t.sent == False
    assert t.filled == False
    assert t.oid == None
    assert t.symbol == None
        
    print(test_order)