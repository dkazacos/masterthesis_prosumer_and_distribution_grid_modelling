# -*- coding: utf-8 -*-
"""
Created on Sat Feb  1 16:11:55 2020

@author: Duarte Kazacos
"""

import pandas as pd

class BatterySimple(object):
    
    state = 'Fully charged'
    
    def __init__(self, p_kw=None, capacity=7.5, meta=None, signal=None):
        
        """
        Linear behavior of charge and discharge of a battery. No
        physical process is considered in this model. Battery has
        a capacity that dictates power In/Out behavior
        """
        
        self.p_kw       = p_kw                  # power exchange [kW] (< 0 charging)
        self.capacity   = capacity              # capacity of battery [kWh]
        self.meta       = {'P'          : [],   # dictionary of data
                           'p_reject'   : [],   # rejected by battery
                           'SOC'        : [],   # state of charge
                           'log'        : [],   # occurrences
                           }     
        self.signal     = signal            # resembles signals from outside
    
    def get_soc(self):
        if self.state == None:
            return 100
        else:
            return self.meta['SOC'][-1]
    
    def get_state(self):
        return self.state
    
    def get_data(self):
        return pd.DataFrame(self.meta)
    
    def get_capacity(self):
        return self.capacity
    
    def bms(self):
        
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
        """
        self.p_kw   = p_kw
        h           = timestep/3600
        st          = self.get_state()
        p           = self.bms()
        c           = self.capacity
        
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
            

class cpu(object):
    
    """
    Documentation
    
    """
    
    def __init__(self, p_pv=None, p_load=None, b_type='linear', switch_b=None, switch_pv=None):
        
        """
        Documentation
        """
        
        self.p_pv       = p_pv
        self.p_load     = p_load
        self.b_type     = b_type
        if self.b_type == "linear":
            self.battery = BatterySimple()
        # elif self.b_type == "phys":
        #     self.battery = Battery()
        self.switch_b   = switch_b
        self.switch_pv  = switch_pv
        self.meta       = {'p_load'             : [],
                           'p_pv'               : [],
                           'p_battery_flow'     : [],
                           'p_grid_flow'        : [],
                           'battery_status'     : [],
                           'grid_status'        : [],
                           'log'                : [],
                           }
    
    def get_data(self):
        return pd.DataFrame(self.meta)
    
    def get_battery_meta(self):
        return self.battery.meta
    
    def get_battery_data(self):
        return self.battery.get_data()
    
    def get_battery_soc(self):
        return self.battery.get_soc()
    
    def control(self, p_pv, p_load, timestep):
        
        """
        Documentation
        """
        
        self.meta['p_pv'].append(p_pv)
        self.meta['p_load'].append(p_load)
        p_flow = p_load - p_pv

        self.battery.process(p_flow, timestep)
        self.meta['p_grid_flow'].append(self.battery.meta['p_reject'][-1])
        self.meta['p_battery_flow'].append(self.battery.meta['P'][-1])
                
        if p_flow > 0 and self.battery.meta['p_reject'][-1] < 0:
            self.meta['grid_status'].append(-1)
            self.meta['battery_status'].append(-1)
            self.meta['log'].append('discharge of battery and supply from grid')
        elif p_flow > 0 and self.battery.meta['p_reject'][-1] == 0:
            self.meta['grid_status'].append(0)
            self.meta['battery_status'].append(-1)
            self.meta['log'].append('demand satisfied by battery. No grid flow')
        elif p_flow < 0 and self.battery.meta['p_reject'][-1] > 0:
            self.meta['grid_status'].append(1)
            self.meta['battery_status'].append(1)
            self.meta['log'].append('charge of battery and grid feed-in')
        elif p_flow < 0 and self.battery.meta['p_reject'][-1] == 0:
            self.meta['grid_status'].append(0)
            self.meta['battery_status'].append(1)
            self.meta['log'].append('surplus absorbed by battery. No grid flow')

class PVgen(object):
    
    """
    """
    
    def __init__(self, irr_sol=None, sys_loss=None, oda_t=None, rated_p=None):
        
        self.irr_sol = irr_sol
        self.sys_loss = sys_loss
        self.oda_t = oda_t
        self.rated_p = rated_p
        self.meta = {'irr_sol'  : [],
                     'oda_t'    : [],
                    }
        
    def get_rated_power(self):
        return self.rated_p
    
    def get_sys_loss(self):
        return self.sys_loss
    
    def get_data(self):
        return pd.DataFrame(self.meta)
    
    def production(self):
        
        return self.rated_p*self.sys_loss # TODO! placeholder for PV model

class Prosumer(object):
    
    """
    """
    
    def __init__(self, irrad_data, load_demand, batt_capacity, chp):
        self.irrad_data = irrad_data
        self.load_demand = load_demand
        self.batt_capacity = batt_capacity
    
    def get_irrad_data(self):
        return self.irrad_data
    
    def get_load_demand(self):
        return self.load_demand
    
    def get_battery_capacity(self):
        return self.batt_capacity