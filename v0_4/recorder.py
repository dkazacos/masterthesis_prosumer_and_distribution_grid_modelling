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

    def last_occurrence(self, with_name=False):
        """
        Returns a list with the last ocurrence recorded in a recorder
        meta dictionaty
        
        with_name : bool, default False
            if True, the output list is composed of tuples whose first
            element is the id of the recorder variable and whose second
            element is the value itself
        """
        l = []
        if with_name:
            for key, val in self.meta.items():
                l.append((key, val[-1]))
        elif not with_name:
            for key, val in self.meta.items():
                l.append(val[-1])
        return l