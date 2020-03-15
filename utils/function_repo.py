# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 21:55:22 2020

@author: Seta
"""

import pandas as pd

def parse_hours(data):
    """
    Converts hours 0..24 to 0..23
    """
    data.index=data.index.str.replace('24:','00:')

def timegrid(data):
    """
    Extracts time step (in seconds) from the time grid property of data.
    Data must be pandas DataFrame or Series
    """
    tg = data.index

    if data.index.dtype == object:
        if any('24:' in string for string in data.index.tolist()):
            data.index=data.index.str.replace('24:','00:')
            tg=tg.str.replace('24:', '00:')
        tg = pd.to_datetime(tg)
        return (tg[1] - tg[0]) // pd.Timedelta('1s')

    elif tg.dtype != object:
        return (tg[1] - tg[0]) // pd.Timedelta('1s')