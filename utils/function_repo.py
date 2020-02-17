# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 21:55:22 2020

@author: Seta
"""

import pandas as pd

def timegrid(self):
    """
    Extracts time step (in seconds) from the time grid property of data.
    Data must be pandas DataFrame or Series
    """
    if self.p_load.index.dtype == object:
        self.p_load.index = pd.to_datetime(self.p_load.index)
        return (self.p_load.index[1] - self.p_load.index[0]) // pd.Timedelta('1s')
    
    elif self.p_kw.index.dtype != object:
        return (self.p_load.index[1] - self.p_load.index[0]) // pd.Timedelta('1s')