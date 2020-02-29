# -*- coding: utf-8 -*-
"""
Created on Sat Feb 29 20:13:35 2020

@author: Seta
"""

import pandas as pd
from Storage import BatterySimple
from PVgen import PVgen

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
        #                             ncells      = self.ncells,
        #                             cn          = self.cn,
        #                             vn          = self.vn,
        #                             dco         = self.dco,
        #                             cco         = self.cco,
        #                             max_c_rate  = self.max_c_rate,
        #                             )
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