# -*- coding: utf-8 -*-
"""
Created on Sat Feb  1 16:11:55 2020

@author: Duarte Kazacos
"""

import sys
sys.path.append('..')
import pandas as pd
import numpy as np
import math
import decimal
import matplotlib.pyplot as plt
from utils.function_repo import timegrid
# from Storage import Battery

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
        area of a single solar panel

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

    def __init__(self,
                 pv_kw          = None,
                 num_panels     = None,
                 panel_peak_p   = 0.3,
                 pv_eff         = 0.18,
                 roof_area      = None,
                 pv_total_loss  = 0.0035,
                 module_area    = 1.96,
                 oda_t          = None,
                 ):

        self.pv_kw          = pv_kw
        self.num_panels     = num_panels
        self.panel_peak_p   = panel_peak_p
        self.pv_eff         = pv_eff
        self.roof_area      = roof_area
        self.pv_total_loss  = pv_total_loss
        self.module_area    = module_area
        self.oda_t          = oda_t
        self.meta           = {
                               'irr_sol'  : [],
                               # 'oda_t'    : [],
                               }
        if not self.pv_kw:
            if self.num_panels:
                self.pv_kw = self.num_panels * self.panel_peak_p
                if self.roof_area:
                    if self.num_panels * self.module_area > math.floor(self.roof_area / self.module_area):
                        raise AttributeError('Invalid number of PVgen panels: %s. Won´t fit in roof area: %s m2 for a module area of %s m2' % (self.num_panels, self.roof_area, self.module_area))
            elif self.roof_area and not self.num_panels:
                self.num_panels = math.floor(self.roof_area / self.module_area)
                self.pv_kw = self.num_panels * self.panel_peak_p
            else:
                print('Missing args: see PVgen class documentation. Need pv_kw, num_panels or roof_area')
        elif self.pv_kw and not self.num_panels:
            if self.pv_kw < 0:
                raise AttributeError('PV installed power cannot be a negative number')
            if self.roof_area:
                if self.pv_kw / self.panel_peak_p * self.module_area > self.roof_area:
                    raise AttributeError('Invalid PVgen installed power. Not enough roof area for given module characteritics to yield %s kW. Reduce PV installed power or increase roof area' % self.pv_kw)
            if decimal.Decimal('%s' % self.pv_kw) % decimal.Decimal('%s' % self.panel_peak_p) != 0:
                self.num_panels = math.ceil(self.pv_kw / self.panel_peak_p)
                self.pv_kw = self.num_panels * self.panel_peak_p
                raise Warning('Module characteristics require chosen PVgen installed power to be adjusted to %s kW. See class default args' % self.pv_kw)
            else:
                self.num_panels = self.pv_kw / self.panel_peak_p
        
    def get_installed_pv(self):
        """
        Returns the PV installed power in kW
        """
        return self.pv_kw
    
    def get_pv_sys_loss(self):
        """
        Returns the PV total power loss in per unit
        """
        return self.pv_total_loss
    
    def get_pv_data(self):
        """
        Returns pandas dataframe composed by object's meta dictionray of data
        """
        return pd.DataFrame(self.meta)
    
    def production(self, irr_sol, timestep):
        """
        A simple model of the PV power pordocution is executed by this function

        Parameters
        ----------
        irr_sol : float
            Irradiance characterizes the amount of power output that can be
            generated by the PV installation. It is expected to receive an
            irradiance in Wh/m2 for a time interval

        Returns
        -------
        float
            Power generation from PV installation at a given timestamp

        """
        p_sun_wh = irr_sol * self.module_area * self.num_panels
        p_sun_kw = p_sun_wh / timestep * 3.6
        if p_sun_kw > self.get_installed_pv():
            return self.get_installed_pv() * (1. - self.pv_total_loss)
        else:
            return p_sun_kw * (1. - self.pv_total_loss)

class CPU(BatterySimple, PVgen):
    
    """
    Control process unit allows for data transfer throughout the prosumer
    simulation. Control unit for power flow from/to the battery and from/to 
    the grid

    Parameters
    ----------
    b_type : str, default 'linear'
        type of battery to be used by the simulation. 
        'linear' battery is an instance of BatterySimple class.
        'phys' battery is an instance of a more advanced physical model of a
        battery. An instance of the class Battery from Storage.py module

    switch_b : int, default None
        switch that bypasses the battery. 0 or 1 for closed or opened

    switch_pv : int, default None
        switch that bypasses the PV installation. 0 or 1 for closed or opened

    battery_capacity: float, default 7.5 kWh
        capacity of the battery in kWh

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
        area of a single solar panel

    oda_t : float, default None
        outdoor air temperature data. Power output dependency on outdoor
        temperature is not yet defined.
        
    Return
    ----------

    """
    
    signal   = 'self-consumption'   # also: 'grid high voltage', 'reactive feed-in'
    strategy = 'pv-priority'        # also: 'grid-friendly', 'cooperative'

    def __init__(self,
                  # p_pv            = None,
                  # p_load          = None,
                  b_type            = 'linear',
                  switch_b          = None,
                  switch_pv         = None,
                  # p_kw            = None,
                  battery_capacity  = 7.5,
                  # signal          = None,
                  ncells            = 1000,
                  cn                = 2.55,
                  vn                = 3.7,
                  dco               = 3.0,
                  cco               = 4.2,
                  max_c_rate        = 10,
                  pv_kw             = None,
                  num_panels        = None,
                  panel_peak_p      = 0.3,
                  pv_eff            = 0.18,
                  roof_area         = None,
                  pv_total_loss     = 0.0035,
                  module_area       = 1.96,
                  oda_t             = None,
                  ):

        # self.p_pv             = p_pv
        # self.p_load           = p_load
        self.b_type             = b_type
        self.switch_b           = switch_b
        self.switch_pv          = switch_pv
        # self.p_kw             = p_kw
        self.battery_capacity   = battery_capacity
        # self.signal           = signal
        self.ncells             = ncells
        self.cn                 = cn
        self.vn                 = vn
        self.dco                = dco
        self.cco                = cco
        self.max_c_rate         = max_c_rate
        self.pv_kw              = pv_kw
        self.num_panels         = num_panels
        self.panel_peak_p       = panel_peak_p
        self.pv_eff             = pv_eff
        self.roof_area          = roof_area
        self.pv_total_loss      = pv_total_loss
        self.module_area        = module_area
        self.oda_t              = oda_t
        if self.b_type == "linear":
            self.battery = BatterySimple(
                                         # p_kw           = self.p_kw,
                                         battery_capacity = self.battery_capacity,
                                         # signal         = self.signal,
                                         )
        # elif self.b_type == "phys":
        #     self.battery = Battery(
        #                            ncells      = self.ncells,
        #                            cn          = self.cn,
        #                            vn          = self.vn,
        #                            dco         = self.dco,
        #                            cco         = self.cco,
        #                            max_c_rate  = self.max_c_rate,
        #                            )
        self.pvgen  = PVgen(
                            pv_kw           = self.pv_kw,
                            num_panels      = self.num_panels,
                            panel_peak_p    = self.panel_peak_p,
                            pv_eff          = self.pv_eff,
                            roof_area       = self.roof_area,
                            pv_total_loss   = self.pv_total_loss,
                            module_area     = self.module_area,
                            oda_t           = self.oda_t,
                            )
        self.meta   = {
                       'timestamp'          : [],
                       'p_load'             : [],
                       'p_pv'               : [],
                       'p_battery_flow'     : [],
                       'battery_SOC'        : [],
                       'battery_status'     : [],
                       'p_grid_flow'        : [],
                       'grid_status'        : [],
                       'log'                : [],
                       }
    
    def get_cpu_data(self):
        """
        Returns pandas dataframe composed by object's meta dictionary of data
        """
        return pd.DataFrame(self.meta, index=self.meta['timestamp'])
  
    def add_timestamp(self, timestamp):
        """
        Extracts the datetime string at every time step of the simulation and
        appends it to object's meta dictionary of data for final call to
        results
        
        Parameters
        ----------
        timestep : float, default None
            number of seconds between every time step of the simulation
        """
        self.meta['timestamp'].append(timestamp)
    
    def control(self, irr_sun, p_load, timestep):
        """
        Function that dictates the behavior of the power flow among the
        components of a Prosumer object and in relationship with the grid
        
        Parameters
        ----------
        irr_sun : float, default None
            solar irradiation at a given time step of the simulation in Wh/m2

        p_load : float, default None
            power requirements of Prosumer at a given time step of the
            simulation in kWh during timestep time

        timestep : float, default None
            number of seconds between every time step of the simulation
        """        
        
        p_pv    = self.pvgen.production(irr_sun, timestep)
        p_flow  = p_load - p_pv
        self.battery.process(p_flow, timestep)
        self.meta['p_pv'].append(p_pv)
        self.meta['p_load'].append(p_load)
        self.meta['p_grid_flow'].append(self.battery.meta['p_reject'][-1])
        self.meta['p_battery_flow'].append(self.battery.meta['P'][-1])
        self.meta['battery_SOC'].append(self.battery.meta['SOC'][-1])

        if p_flow > 0 and self.battery.meta['p_reject'][-1] < 0: # battery rejects discharging
            self.meta['grid_status'].append(-1)
            if self.meta['p_battery_flow'][-1] == 0:
                self.meta['battery_status'].append(0)
                self.meta['log'].append('supply from grid')
            else:
                self.meta['battery_status'].append(-1)
                self.meta['log'].append('battery discharge and supply from grid')
        elif p_flow > 0 and self.battery.meta['p_reject'][-1] == 0: # battery accepts discharging
            self.meta['grid_status'].append(0)
            self.meta['battery_status'].append(-1)
            self.meta['log'].append('demand satisfied by battery. No grid flow')
        elif p_flow < 0 and self.battery.meta['p_reject'][-1] > 0: # battery rejects charging
            self.meta['grid_status'].append(1)
            if self.meta['p_battery_flow'][-1] == 0:
                self.meta['battery_status'].append(0)
                self.meta['log'].append('grid feed-in')
            else:
                self.meta['battery_status'].append(1)
                self.meta['log'].append('battery charge and grid feed-in')
        elif p_flow < 0 and self.battery.meta['p_reject'][-1] == 0: # battery accepts charging
            self.meta['grid_status'].append(0)
            self.meta['battery_status'].append(1)
            self.meta['log'].append('surplus absorbed by battery. No grid flow')

class Prosumer(CPU):
    
    """
    Prosumer class that resembles the behavior of a houshold that consumes and
    produces electric power

    Parameters
    ----------
    load_demand : pandas Series, default None
        time series of load profile data for a prosumer

    b_type : str, default 'linear'
        type of battery to be used by the simulation. 
        'linear' battery is an instance of BatterySimple class.
        'phys' battery is an instance of a more advanced physical model of a
        battery. An instance of the class Battery from Storage.py module

    switch_b : int, default None
        switch that bypasses the battery. 0 or 1 for closed or opened

    switch_pv : int, default None
        switch that bypasses the PV installation. 0 or 1 for closed or opened

    battery_capacity: float, default 7.5 kWh
        capacity of the battery in kWh

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
        area of a single solar panel

    oda_t : float, default None
        outdoor air temperature data. Power output dependency on outdoor
        temperature is not yet defined.
        
    Return
    ----------
    
    """
    
    signal = 'self-consumption'

    def __init__(self,
                 # irrad_data       = None,
                 load_demand        = None,
                 # p_pv             = None,
                 # p_load           = None,
                 b_type             = 'linear',
                 switch_b           = None,
                 switch_pv          = None,
                 # p_kw             = None,
                 battery_capacity   = 7.5,
                 # signal           = None,
                 ncells             = 1000,
                 cn                 = 2.55,
                 vn                 = 3.7,
                 dco                = 3.0,
                 cco                = 4.2,
                 max_c_rate         = 10,
                 pv_kw              = None,
                 num_panels         = None,
                 panel_peak_p       = 0.3,
                 pv_eff             = 0.18,
                 roof_area          = None,
                 pv_total_loss      = 0.0035,
                 module_area        = 1.96,
                 oda_t              = None,
                 ):

        # self.irrad_data       = irrad_data
        self.load_demand        = load_demand
        # self.p_pv             = p_pv
        # self.p_load           = p_load
        self.b_type             = b_type
        self.switch_b           = switch_b
        self.switch_pv          = switch_pv
        # self.p_kw             = p_kw
        self.battery_capacity   = battery_capacity
        # self.signal           = signal
        self.ncells             = ncells
        self.cn                 = cn
        self.vn                 = vn
        self.dco                = dco
        self.cco                = cco
        self.max_c_rate         = max_c_rate
        self.pv_kw              = pv_kw
        self.num_panels         = num_panels
        self.panel_peak_p       = panel_peak_p
        self.pv_eff             = pv_eff
        self.roof_area          = roof_area
        self.pv_total_loss      = pv_total_loss
        self.module_area        = module_area
        self.oda_t              = oda_t

        self.cpu            = CPU(
                                  # p_pv            = self.p_pv,
                                  # p_load          = self.p_load,
                                  b_type            = self.b_type,
                                  switch_b          = self.switch_b,
                                  switch_pv         = self.switch_pv,
                                  # p_kw            = self.p_kw,
                                  battery_capacity  = self.battery_capacity,
                                  # signal          = self.signal,
                                  ncells            = self.ncells,
                                  cn                = self.cn,
                                  vn                = self.vn,
                                  dco               = self.dco,
                                  cco               = self.cco,
                                  max_c_rate        = self.max_c_rate,
                                  pv_kw             = self.pv_kw,
                                  num_panels        = self.num_panels,
                                  panel_peak_p      = self.panel_peak_p,
                                  pv_eff            = self.pv_eff,
                                  roof_area         = self.roof_area,
                                  pv_total_loss     = self.pv_total_loss,
                                  module_area       = self.module_area,
                                  oda_t             = self.oda_t,
                                  )
        self.battery        = self.cpu.battery
        self.pvgen          = self.cpu.pvgen
        self.meta           = self.cpu.meta

    # def get_irrad_data(self):
    #     return self.irrad_data

    def get_load_demand(self):
        """
        Returns load profile data as a pandas series object
        """
        return self.load_demand

    def active(self, irrad_data):
        """
        Runs the data transfer at every timestamp of the simulation. This
        method calls CPU's control in a discrete fashion and allows for
        breaking and continuing the process given external signals
        
        Parameters
        ----------
        irrad_data : pandas Series, default None
            time series of irradiation data that will be passed to the PV
            installation in Wh/m2
        """

        timestep = timegrid(irrad_data)
        i        = 0
        while self.signal =='self-consumption':
            irr_sun = irrad_data.iloc[i]
            p_load  = self.load_demand.iloc[i]
            self.cpu.control(irr_sun, p_load, timestep)
            self.cpu.add_timestamp(irrad_data.index[i])
            i += 1
            if i >= len(irrad_data) or i >= len(self.load_demand):
                self.signal = 'ended'
                break
            # TODO! introduce logic for variation of signals

if __name__ == "__main__":

    # ========================================================================
    # Data preparation
    # Import irradiance test data
    irr = pd.read_csv(
                      filepath_or_buffer = '../data/1minIntSolrad-07-2006.csv',
                      sep                = ';',
                      skiprows           = 25,
                      parse_dates        = [[0,1]],
                      index_col          = 0,
                      )
    # Import load_profile test data
    load_data = pd.read_csv(
                            filepath_or_buffer = '../data/1MinIntSumProfiles-Apparent-2workingpeople.csv',
                            sep                = ';',
                            usecols            = [1,2],
                            parse_dates        = [1],
                            index_col          = 0,
                            )
    load_data.index = pd.to_datetime(load_data.index) + pd.Timedelta(minutes=1)
    irrad_data      = irr.iloc[:, 3]
    load_demand     = load_data.iloc[:, 0]
    if any(',' in string for string in load_demand):
        load_demand = load_demand.str.replace(',', '.')
        load_demand = 30*pd.to_numeric(load_demand)

    # ========================================================================
    # Test model and get results
    META = {
            'pv_kw'         : 2.1,
            'load_demand'   : load_demand,
            }
    psimp = Prosumer(
                     b_type             = 'linear',
                     battery_capacity   = 3.5,
                     **META,
                     )

    # pphys = Prosumer(
    #                 b_type = 'phys',
    #                 ncells = 1000,
    #                 **META,
    #                 )

    psimp.active(
                irrad_data = irrad_data,
                )

    # pphys.active(
    #             irrad_data = irrad_data,
    #             )

    prosumer_dict = {}
    prosumer_dict['res_simp'] = psimp.get_cpu_data()
    # prosumer_dict['res_phys'] = pphys.get_cpu_data()

    # ========================================================================
    # Show some results
    for key, val in prosumer_dict:
        fig, ax = plt.subplots(figsize=(12,12))

        ax.plot(val.p_load[720:960], 'orange', label='load')
        ax.plot(val.p_pv[720:960], 'r', label='pv')
        ax.plot(val.p_battery_flow[720:960], 'g', label='batt')
        ax.plot(val.p_grid_flow[720:960], 'b', label='grid')
        start, end = ax.get_xlim()
        ax.xaxis.set_ticks(np.arange(start, end, 10))
        fig.autofmt_xdate()
        ax.legend()
        plt.title('Power flow during 1st simulated day', fontsize=18)