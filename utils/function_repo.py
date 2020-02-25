# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 21:55:22 2020

@author: Seta
"""

import pandas as pd

def timegrid(data):
    """
    Extracts time step (in seconds) from the time grid property of data.
    Data must be pandas DataFrame or Series
    """
    if data.p_load.index.dtype == object:
        data.p_load.index = pd.to_datetime(data.p_load.index)
        return (data.p_load.index[1] - data.p_load.index[0]) // pd.Timedelta('1s')
    
    elif data.p_kw.index.dtype != object:
        return (data.p_load.index[1] - data.p_load.index[0]) // pd.Timedelta('1s')