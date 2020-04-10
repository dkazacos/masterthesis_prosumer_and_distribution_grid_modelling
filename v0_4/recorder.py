# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 18:28:30 2020

@author: Seta
"""

import pandas as pd

class Recorder(object):
    def __init__(self, *args):
        self.meta = {}
        for key in args:
            self.meta[key] = []

    def record(self, **kwargs):
        for key, val in kwargs.items():
            self.meta[key].append(val)

    def get_data(self):
         return pd.DataFrame(self.meta)