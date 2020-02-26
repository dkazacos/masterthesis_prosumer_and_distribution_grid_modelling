# -*- coding: utf-8 -*-
"""
Created on Sat Feb  1 16:11:55 2020

@author: Duarte Kazacos
"""

import pandas as pd
import math
# from utils.function_repo import timegrid

class BatterySimple(object):
    """
    Linear behavior of charge and discharge of a battery. No
    physical process is considered in this model. Battery has
    a capacity that dictates power In/Out behavior

    Parameters
    ----------
    p_kw : float, default None
        power flow that charges or discharges battery in kW

    capacity : float, default 7.5
        capacity of the battery in kWh

    meta : dict, default None
        dictionary containing process data

    signal : str, default None
        place-holder for external control signals

    Returns
    ----------

    """

    state = 'Fully charged'
    
    def __init__(self, p_kw=None, capacity=7.5, meta=None, signal=None):

        self.p_kw       = p_kw                  # power exchange [kW] (< 0 charging)
        self.capacity   = capacity              # capacity of battery [kWh]
        self.meta       = {'P'          : [],   # dictionary of data
                           'p_reject'   : [],   # rejected by battery
                           'SOC'        : [],   # state of charge
                           'log'        : [],   # occurrences
                           }     
        self.signal     = signal            # resembles signals from outside
    
    def get_soc(self):
        if len(self.meta['SOC']) == 0:
            return 100
        else:
            return self.meta['SOC'][-1]
    
    def get_state(self):
        return self.state
    
    def get_battery_data(self):
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
            

class CPU(object):
    
    """
    Documentation
    
    """
    
    signal   = 'self-consumption'   # also: 'grid high voltage', 'reactive feed-in'
    strategy = 'pv-priority'        # also: 'grid-friendly', 'cooperative'

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
    
    def get_cpu_data(self):
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
    PV installation is characterized by the following arguments

    Parameters
    ----------
    pv_kw : float, default None
        installed peak power mounted on roof top in kW

    num_panels : int default None
        number of solar panels mounted on roof top. Need

    panel_peak_p : float, default 0.3
        rated power of a single solar panel in kW

    pv_eff : float, default 0.18
        efficiency of single solar panel

    roof_area : float, default None
        available roof area to mount PV installation

    total_loss : float, default 0.0035
        total loss due to cable transmission

    module_area : float, default 1.96 m2

    oda_t : float, default None
        outdoor air temperature data. Power output dependency on outdoor
        temperature is not yet defined.

    ----------
    Accepts combination of arguments to fully characterize a PV installation

        .. PV peak power installed (pv_kw) fully characterizes installation

        .. number of panels (num_panels) fully characterizes installation

        .. available roof area (roof_area) fully characterizes installation

    Returns
    -------
    float
        Power generation from PV installation at a given timestamp provided in
        production() method
    """

    def __init__(self, pv_kw = None, num_panels=None, panel_peak_p=0.3, pv_eff=0.18, roof_area=None, total_loss=0.0035, module_area=1.96, oda_t=None):

        self.pv_kw          = pv_kw
        self.num_panels     = num_panels
        self.panel_peak_p   = panel_peak_p
        self.pv_eff         = pv_eff
        self.roof_area      = roof_area
        self.total_loss     = total_loss
        self.module_area    = module_area
        self.oda_t          = oda_t
        self.meta           = {'irr_sol'  : [],
                               # 'oda_t'    : [],
                               }

    def get_installed_power(self):
        
        if self.pv_kw:
            return self.pv_kw
        elif self.num_panels:
            return self.num_panels*self.panel_peak_p
        elif self.roof_area:
            num_panels = math.floor(self.roof_area/self.module_area)
            self.num_panels = num_panels
            return num_panels * self.panel_peak_p
        else:
            return 'Missing args: see documentation. Need pv_kw, num_panels or roof_area'
    
    def get_sys_loss(self):
        return self.total_loss
    
    def get_pv_data(self):
        return pd.DataFrame(self.meta)
    
    def production(self, irr_sol):
        """

        Parameters
        ----------
        irr_sol : float
            Irradiance characterizes the amount of power output that can be
            generated by the PV installation. It is expected to receive an
            irradiance in W/m2

        Returns
        -------
        float
            Power generation from PV installation at a given timestamp

        """

        p_sun = irr_sol * self.module_area / 1000
        
        if p_sun > self.get_installed_power():
            return self.get_installed_power() * self.total_loss
        else:
            return p_sun

class Prosumer(BatterySimple, CPU, PVgen):
    
    """
    """
    
    def __init__(self,
                 irrad_data     = None,
                 load_demand    = None,
                 pv_kw          = None,
                 num_panels     = None,
                 panel_peak_p   = 0.3,
                 pv_eff         = 0.18,
                 roof_area      = None,
                 total_loss     = 0.0035,
                 module_area    = 1.96,
                 oda_t          = None,
                 p_pv           = None,
                 p_load         = None,
                 p_kw           = None,
                 capacity       = 7.5,
                 signal         = None,
                 ):

        self.irrad_data     = irrad_data
        self.load_demand    = load_demand
        self.pv_kw          = pv_kw
        self.num_panels     = num_panels
        self.panel_peak_p   = panel_peak_p
        self.pv_eff         = pv_eff
        self.roof_area      = roof_area
        self.total_loss     = total_loss
        self.module_area    = module_area
        self.oda_t          = oda_t
        self.p_pv           = p_pv
        self.p_load         = p_load
        self.p_kw           = p_kw
        self.capacity       = capacity
        self.signal         = signal
        self.battery        = BatterySimple(p_kw=self.p_kw,
                                            capacity=self.capacity,
                                            signal=self.signal)
        self.cpu            = CPU(p_pv=self.p_pv,
                                  p_load=self.p_load)
        self.pv_gen         = PVgen(pv_kw=self.pv_kw,
                                    num_panels=self.num_panels,
                                    panel_peak_p=self.panel_peak_p,
                                    pv_eff=self.pv_eff,
                                    roof_area=self.roof_area,
                                    total_loss=self.total_loss,
                                    module_area=self.module_area,
                                    oda_t=self.oda_t)

    def get_irrad_data(self):
        return self.irrad_data

    def get_load_demand(self):
        return self.load_demand

    def get_battery_capacity(self):
        return self.battery.get_capacity()

    def active(self, signal):
        """
        """

        timestep    = timegrid(self.irrad_data)
        p_pv        = self.irrad_data
        p_load      = self.load_demand
        i, j        = 0

        while signal=='green':
            self.cpu.signal = signal
            self.cpu.control(p_pv.iloc[i, 0], p_load.iloc[j, 0], timestep)

            i += 1
            j += 1