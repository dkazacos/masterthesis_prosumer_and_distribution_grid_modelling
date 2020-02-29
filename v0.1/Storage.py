# -*- coding: utf-8 -*-
"""
Created on Sat Feb 29 20:09:27 2020

@author: Seta
"""

import pandas as pd

class BatterySimple(object):
    """
    Linear behavior of charge and discharge of a battery. No
    physical process is considered in this model. Battery has
    a capacity that dictates power In/Out behavior

    Parameters
    ----------
    battery_capacity : float, default 7.5
        capacity of the battery in kWh

    signal : str, default None
        place-holder for external control signals

    Returns
    ----------

    """

    state   = 'Fully charged'
    signal  = 'self-consumption'
    p_kw    = None
    
    def __init__(self,
                 # p_kw             = None,
                 battery_capacity   = 7.5,
                 # signal           = None,
                 ):

        # self.p_kw             = p_kw                  # power exchange [kW] (< 0 charging)
        self.battery_capacity   = battery_capacity      # capacity of battery [kWh]
        # self.signal           = signal                # resembles signals from outside
        self.meta               = {
                                   'P'          : [],   # dictionary of data
                                   'p_reject'   : [],   # rejected by battery
                                   'SOC'        : [],   # state of charge
                                   'log'        : [],   # occurrences
                                   }
        if self.battery_capacity < 0:
            raise AttributeError('Battery capacity cannot be a negative number')
    
    def get_battery_soc(self):
        """
        Returns the battery state of charge in %
        """
        if len(self.meta['SOC']) == 0:
            return 100
        else:
            return self.meta['SOC'][-1]
    
    def get_battery_state(self):
        """
        Returns the current state of a battery instance as a string log
        """
        return self.state
    
    def get_battery_data(self):
        """
        Returns a pandas dataframe composed by object's meta dictionary
        """
        return pd.DataFrame(self.meta)
    
    def get_battery_capacity(self):
        """
        Returns the battery capacity in kWh
        """
        return self.battery_capacity
    
    def bms(self):
        """
        Battery Management System (BMS). Dictates the acceptance of
        rejection of power flow by the battery
        """
        if self.p_kw < 0:
            if self.state == 'Fully charged':
                return 0
            elif self.state in ['Operational', 'Depleted']:
                return self.p_kw
        elif self.p_kw > 0:
            if self.state == 'Depleted':
                return 0
            elif self.state in ['Operational', 'Fully charged']:
                return self.p_kw
        elif self.p_kw == 0:
            return self.p_kw
    
    def process(self, p_kw, timestep):
        
        """
        Populates an object's meta dictionary with data comming from the
        power flow through the battery after BMS filtering
        """
        self.p_kw   = p_kw
        h           = timestep/3600
        st          = self.get_battery_state()
        p           = self.bms()
        c           = self.battery_capacity
        
        if p > 0: # discharge battery
            if len(self.meta['SOC']) == 0:
                Q = c - p*h
            else:
                Q = c*self.meta['SOC'][-1]/100 - p*h
            if Q < 0:
                self.state = 'Depleted'
                self.meta['p_reject'].append(Q/h)   # rejected negative power (negative for grid)
                if len(self.meta['SOC']) == 0:
                    self.meta['P'].append(c/h)      # accepted positive power (discharge)
                else:
                    self.meta['P'].append((c*self.meta['SOC'][-1]/100)/h)
                self.meta['SOC'].append(0)
                self.meta['log'].append('discharged, depleted')
            elif Q >= 0:
                self.state = 'Operational'
                self.meta['p_reject'].append(0)
                self.meta['P'].append(p)
                self.meta['SOC'].append(Q/c*100)
                self.meta['log'].append('discharging')

        elif p < 0: # charge battery
            if len(self.meta['SOC']) == 0:
                Q = c - p*h
            else:
                Q = c*self.meta['SOC'][-1]/100 - p*h
            if Q > c:
                self.state = 'Fully charged'
                self.meta['p_reject'].append((Q-c)/h)                       # rejected positive power (positive for grid)
                self.meta['P'].append(-c*(1-self.meta['SOC'][-1]/100)/h)    # accepted negative power (charge)
                self.meta['SOC'].append(100)
                self.meta['log'].append('charged, fully charged')
            elif Q <= c:
                self.state = 'Operational'
                self.meta['p_reject'].append(0)
                self.meta['P'].append(p)
                self.meta['SOC'].append(Q/c*100)
                self.meta['log'].append('charging')
        
        elif p == 0: # no flow in/out battery
            if st == 'Fully charged':
                self.meta['SOC'].append(100)
                self.meta['p_reject'].append(-p_kw)                         # rejected at charging (positive for grid)
            elif st == 'Depleted':
                self.meta['SOC'].append(0)
                self.meta['p_reject'].append(-p_kw)                         # rejected at discharging (negative for grid)
            elif st == 'Operational':
                if len(self.meta['SOC']) == 0:
                    self.meta['SOC'].append(100)
                else:
                    self.meta['SOC'].append(self.meta['SOC'][-1])
            self.meta['P'].append(p)
            self.meta['log'].append('No power flow through battery')