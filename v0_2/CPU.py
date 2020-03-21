# -*- coding: utf-8 -*-
"""
Created on Sat Feb 29 20:13:35 2020

@author: Seta
"""
import sys
sys.path.append('..')
import pandas as pd
import matplotlib.pyplot as plt
from utils.function_repo import timegrid, parse_hours
from Storage import BatterySimple, Battery
from PVgen import PVgen

class CPU(BatterySimple, PVgen):
    
    """
    Control process unit allows for data transfer throughout the prosumer
    simulation. Control unit for power flow from/to the battery and from/to 
    the grid.
    
    This class fully characterizes a single Prosumer

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
                  # oda_t             = None,
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
        # self.oda_t              = oda_t
        if self.b_type == "linear":
            self.battery = BatterySimple(
                                         # p_kw           = self.p_kw,
                                         battery_capacity = self.battery_capacity,
                                         # signal         = self.signal,
                                         )
        elif self.b_type == "phys":
            self.battery = Battery(
                                    ncells      = self.ncells,
                                    cn          = self.cn,
                                    vn          = self.vn,
                                    dco         = self.dco,
                                    cco         = self.cco,
                                    max_c_rate  = self.max_c_rate,
                                    )
        self.pvgen  = PVgen(
                            pv_kw           = self.pv_kw,
                            num_panels      = self.num_panels,
                            panel_peak_p    = self.panel_peak_p,
                            pv_eff          = self.pv_eff,
                            roof_area       = self.roof_area,
                            pv_total_loss   = self.pv_total_loss,
                            module_area     = self.module_area,
                            # oda_t           = self.oda_t,
                            )
        if self.pvgen.pv_kw != self.pv_kw:
            self.pv_kw = self.pvgen.pv_kw
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
        return pd.DataFrame(self.meta)
  
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

    def active(self, irrad_data, load_data):
        """
        Runs the data transfer at every timestamp of the simulation. This
        method calls CPU's control and runs throughout full length load
        demanad and irradiation data statically
        
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
            p_load  = load_demand.iloc[i]
            self.control(irr_sun, p_load, timestep)
            self.add_timestamp(irrad_data.index[i])
            i += 1
            if i >= len(irrad_data) or i >= len(load_demand):
                self.signal = 'ended'
                break
            # TODO! introduce logic for variation of signals

    def run_pflow(self, irrad_data, load_data, timestep, timestamp):
        """
        Runs the data transfer at a given timestamp of the simulation. This
        method calls CPU's control in a discrete fashion and allows for
        breaking and continuing the process given external signals
        
        Parameters
        ----------
        irrad_data : float, default None
            solar irradiation at a given time step of the simulation in Wh/m2

        load_data : float, default None
            power requirements of Prosumer at a given time step of the
            simulation in kWh during timestep time

        timestep : float, default None
            number of seconds between every time step of the simulation
        """
        if self.signal == 'self-consumption':
            self.add_timestamp(timestamp)
            return self.control(irrad_data, load_data, timestep)

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
    # Convert 0..24:00 hours to 0..23:59
    parse_hours(irr)
    load_data.index = pd.to_datetime(load_data.index, dayfirst=True) + pd.Timedelta(minutes=1)
    load_demand     = load_data.iloc[:, 0]
    irrad_data      = irr.iloc[:, 3]
    irrad_data.index= pd.to_datetime(irrad_data.index) + pd.DateOffset(years=10)

    if any(',' in string for string in load_demand):
        load_demand = load_demand.str.replace(',', '.')
        load_demand = 30*pd.to_numeric(load_demand)

    # ========================================================================
    # Test model and get results
    META = {
            'pv_kw'         : 2.1,
            }
    psimp = CPU(
                b_type             = 'linear',
                battery_capacity   = 3.5,
                **META,
                )

    # pphys = CPU(
    #             b_type = 'phys',
    #             ncells = 1000,
    #             **META,
    #             )

    # psimp.active(
    #             irrad_data = irrad_data,
    #             load_data = load_demand,
    #             )

    timestep = timegrid(irrad_data)
    for i, (irr, ld) in enumerate(zip(irrad_data, load_demand)):
        psimp.run_pflow(
                        irrad_data  = irr,
                        load_data   = ld,
                        timestep    = timestep,
                        timestamp   = load_demand.index[i],
                        )

    # pphys.active(
    #             irrad_data = irrad_data,
    #             )

    prosumer_dict = {}
    prosumer_dict['res_simp'] = psimp.get_cpu_data()
    prosumer_dict['res_simp'].set_index('timestamp', inplace=True)
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