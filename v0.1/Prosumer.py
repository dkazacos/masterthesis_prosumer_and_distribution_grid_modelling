# -*- coding: utf-8 -*-
"""
Created on Sat Feb  1 16:11:55 2020

@author: Duarte Kazacos
"""

import sys
sys.path.append('..')
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from utils.function_repo import timegrid
from CPU import CPU

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
    for val in prosumer_dict.values():
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