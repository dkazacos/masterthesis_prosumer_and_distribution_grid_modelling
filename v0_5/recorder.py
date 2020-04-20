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
        d = {}
        for key, val in self.meta.items():
            d[key] = val[-1]
        return d

class Counter(object):
    def __init__(self):
        self.recorder = Recorder()

    def binary_count(self, to_count, value, reset_counter_at):
        self.recorder.record(to_count = value)
        if value:
            self.recorder.meta[to_count] = [1]
            return True
        else:
            if not sum(self.recorder.meta[to_count]):
                self.recorder.meta[to_count] = []
                return True
            elif sum(self.recorder.meta[to_count]) != reset_counter_at:
                self.recorder.meta[to_count][-1] = 1
                return False
            else:
                self.recorder.meta[to_count] = []
                return True