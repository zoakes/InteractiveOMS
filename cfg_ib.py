# -*- coding: utf-8 -*-
"""
Created on Mon Jan  3 11:24:40 2022

@author: zach
"""


# Input FRONT months here...
root_to_front = {
    'MES':'MESH2',
    'MNQ':'MNQH2',
    
    'ES':'ESH2',
    'NQ':'NQH2',
    'CL':'CLH2',
    'GC':'GCH2',
    'ZS':'ZSH2'
}
# Not used yet...
root_qty = {
    
    'ES':1,
    'NQ':1,
    'ZS':1,
    'GC':1,
    'CL':1
}

# ------------ These should remain Static for the most part ------------ #

root_exch_ib = {
    'MES':'GLOBEX',
    'MNQ':'GLOBEX',
    
    'ES':'GLOBEX',
    'NQ':'GLOBEX',
    'ZS':'CBOT',
    'CL':'NYMEX',
    'GC':'COMEX'
    }
