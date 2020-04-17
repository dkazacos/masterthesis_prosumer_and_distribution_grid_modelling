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
from recorder import Recorder

class Prosumer(object):

    """
    Control process unit allows for data transfer throughout the prosumer
    simulation. Control unit for power flow from/to the battery and from/to 
    the grid.

    This class fully characterizes a single Prosumer

    Parameters
    ----------
    pvgen: object, default None
        instance of class PVgen which can be fully characterized by its own
        default attributes. See documentation

    battery: object, dafault None
        instance of a class BatterySimple or Battery that can be fully
        characterized by its own default attributes. See documentation
    
    Return
    ----------

    """

    # battery_mode is passed to the battery for consequent operation mode
    battery_mode   = 'self-consumption'   # also: 'buffer-grid' 
    # Strategy is passed to the pv system for consequent operation mode
    pv_strategy = 'self-consumption'   # also: 'full-curtailment', 'partial-curtailment', 'reactive feed-in'

    def __init__(self,
                pvgen,
                battery,
                ):

        self.battery    = battery
        self.pvgen      = pvgen
        self.recorder   = Recorder(
                                'timestamp',
                                'p_load',
                                'p_pv',
                                'p_battery_flow',
                                'battery_SOC',
                                'battery_status',
                                'p_grid_flow',
                                'grid_status',
                                'log',
                                )

    def get_prosumer_data(self):
        """
        Returns pandas dataframe composed by object's recorder meta dictionary
        of data
        """
        return self.recorder.get_data()

    def set_battery_capacity(self, c):
        """
        init parent Battery battery capacity with desired value c in kWh
        """
        self.battery.battery_capacity = c

    def set_pv_installed_power(self, installed_pv):
        """
        init parent PVgen installed pv power with desired value installed_pv in kW
        Careful: pv installed power obeys the limitations of the panel
        characteristics. Make sure to set a power that is multiple of
        PVgen panel_peak_p attribute
        """
        self.pvgen.installed_pv = installed_pv

    def set_battery_mode(self, mode):
        self.battery.set_battery_mode(mode)
        self.battery_mode = mode

    def set_pvgen_strategy(self, strategy):
        self.pvgen.strategy = strategy
        self.pv_strategy = strategy

    def add_timestamp(self, timestamp):
        """
        Extracts the datetime string at every time step of the simulation and
        appends it to object's recorder meta dictionary of data for final call
        to results
        
        Parameters
        ----------
        timestep : float, default None
            number of seconds between every time step of the simulation
        """
        self.recorder.record(timestamp = timestamp)

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
        self.recorder.record(p_pv   = p_pv,
                             p_load = p_load)
        if self.pv_strategy == 'self-consumption':
            self.recorder.record(p_grid_flow = self.battery.recorder.meta['p_reject'][-1])
            self.pvgen.recorder.record(p_curtail = 0)
        elif self.pv_strategy == 'curtailment':
            if self.battery.recorder.meta['p_reject'][-1] >= 0:
                self.recorder.record(p_grid_flow = 0)
                self.pvgen.recorder.record(p_curtail = self.battery.recorder.meta['p_reject'][-1])
            else:
                self.recorder.record(p_grid_flow = self.battery.recorder.meta['p_reject'][-1])
                self.pvgen.recorder.record(p_curtail = 0)
        self.recorder.record(p_battery_flow = self.battery.recorder.meta['P'][-1],
                             battery_SOC = self.battery.recorder.meta['battery_SOC'][-1])

        if p_flow > 0 and self.battery.recorder.meta['p_reject'][-1] < 0: # battery rejects discharging
            self.recorder.record(grid_status = -1)
            if self.recorder.meta['p_battery_flow'][-1] == 0:
                self.recorder.record(battery_status = 0,
                                     log            = 'supply from grid')
            else:
                self.recorder.record(battery_status = -1,
                                     log            = 'battery discharge and supply from grid')
        elif p_flow > 0 and not self.battery.recorder.meta['p_reject'][-1]: # battery accepts discharging
            self.recorder.record(grid_status    = 0,
                                 battery_status = -1,
                                 log            = 'demand satisfied by battery. No grid flow')
        elif p_flow < 0 and self.battery.recorder.meta['p_reject'][-1] > 0: # battery rejects charging
            self.recorder.record(grid_status = 1)
            if self.recorder.meta['p_battery_flow'][-1] == 0:
                self.recorder.record(battery_status = 0,
                                     log            = 'grid feed-in')
            else:
                self.recorder.record(battery_status = 1,
                                     log = 'battery charge and grid feed-in')
        elif p_flow < 0 and not self.battery.recorder.meta['p_reject'][-1]: # battery accepts charging
            self.recorder.record(grid_status    = 0,
                                 battery_status = 1,
                                 log            = 'surplus absorbed by battery. No grid flow')
        elif not p_flow:
            self.recorder.record(grid_status    = 0,
                                 battery_status = 0,
                                 log            = 'demand matches pv yield')

    def run_static_sim(self, irrad_data, load_data, timestep):
        """
        Runs the data transfer at every timestamp of the simulation. This
        method calls Prosumer's control and runs throughout full length load
        demanad and irradiation data statically
        
        Parameters
        ----------
        irrad_data : pandas Series, default None
            time series of irradiation data that will be passed to the PV
            installation in Wh/m2

        load_data : pandas Series, default None
            timeseries of power requirements of Prosumer in kWh
        """

        i = 0
        while self.battery_mode =='self-consumption':
            irr_sun = irrad_data.iloc[i]
            p_load  = load_demand.iloc[i]
            self.control(irr_sun, p_load, timestep)
            self.add_timestamp(irrad_data.index[i])
            i += 1
            if i >= len(irrad_data) or i >= len(load_demand):
                self.battery_mode = 'ended'
                break
            # TODO! introduce logic for variation of battery_modes

    def run_pflow(self, irrad_data, load_data, timestep, timestamp):
        """
        Runs the data transfer at a given timestamp of the simulation. This
        method calls Prosumer's control in a discrete fashion and allows for
        breaking and continuing the process given external battery_modes
        
        Parameters
        ----------
        irrad_data : float, default None
            solar irradiation at a given time step of the simulation in Wh/m2

        load_data : float, default None
            power requirements of Prosumer at a given time step of the
            simulation in kWh during timestep time

        timestep : float, default None
            number of seconds between every time step of the simulation

        timestamp : str, default None
            timestamp corresponding to timestep of simulation
        """

        self.add_timestamp(timestamp)
        self.control(irrad_data, load_data, timestep)

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
            'pvgen'     : PVgen(
                                installed_pv = 2.1,
                                ),
            'battery'   : BatterySimple(
                                        battery_capacity    = 3.5,
                                        initial_SOC         = 90,
                                        min_max_SOC         = (20,80),
                                        ),
            # 'battery'   : Battery(
            #                     battery_capacity    = 3.5,
            #                     initial_SOC         = 90,
            #                     min_max_SOC         = (20,80),
            #                     )
            }
    prosumer = Prosumer(
                **META,
                )
    # prosumer.set_pvgen_strategy('curtailment')
    prosumer.set_pvgen_strategy('self-consumption')
    # prosumer.set_battery_mode('self-consumption')
    prosumer.set_battery_mode('buffer-grid')

    timestep = timegrid(irrad_data)

    # psimp.run_static_sim(
    #                   irrad_data = irrad_data,
    #                   load_data = load_demand,
    #                   timestep = timestep,
    #                   )

    for i, (irr, ld) in enumerate(zip(irrad_data, load_demand)):
        prosumer.run_pflow(
                        irrad_data  = irr,
                        load_data   = ld,
                        timestep    = timestep,
                        timestamp   = load_demand.index[i],
                        )

    # pphys.run_static_sim(
    #                     irrad_data = irrad_data,
    #                     )

    prosumer_dict = {}
    prosumer_dict['res_simp'] = prosumer.get_prosumer_data()
    prosumer_dict['res_simp'].set_index('timestamp', inplace=True)
    # prosumer_dict['res_phys'] = pphys.get_prosumer_data()

    # ========================================================================
    # Show some results
    for val in prosumer_dict.values():
        
        fig, ax1 = plt.subplots(figsize=(12,12))
    
        ln1 = ax1.plot(val.p_load[:480], 'orange', label='load')
        ln2 = ax1.plot(val.p_pv[:480], 'r', label='pv')
        ln3 = ax1.plot(val.p_battery_flow[:480], 'g', label='batt')
        ln4 = ax1.plot(val.p_grid_flow[:480], 'b', label='grid')
        ax2 = ax1.twinx()
        ln5 = ax2.plot(val.battery_SOC[:480], 'black', label='SOC')
        lns = ln1+ln2+ln3+ln4+ln5
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs)
    
        ax1.grid()
        ax1.set_xlabel('Time', fontsize=14)
        ax1.set_ylabel('Power flow (kW)', fontsize=14)
        ax2.set_ylabel('Battery SOC', color='black', fontsize=14)  # we already handled the x-label with ax1
        ax2.set_ylim(0,120)
        # plt.title('Power flow during 1st simulated day', fontsize=18)
        fig.tight_layout()
        
        fig, ax1 = plt.subplots(figsize=(12,12))
    
        ln1 = ax1.plot(val.p_load[480:960], 'orange', label='load')
        ln2 = ax1.plot(val.p_pv[480:960], 'r', label='pv')
        ln3 = ax1.plot(val.p_battery_flow[480:960], 'g', label='batt')
        ln4 = ax1.plot(val.p_grid_flow[480:960], 'b', label='grid')
        ax2 = ax1.twinx()
        ln5 = ax2.plot(val.battery_SOC[480:960], 'black', label='SOC')
        lns = ln1+ln2+ln3+ln4+ln5
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs)
    
        ax1.grid()
        ax1.set_xlabel('Time', fontsize=14)
        ax1.set_ylabel('Power flow (kW)', fontsize=14)
        ax2.set_ylabel('Battery SOC', color='black', fontsize=14)  # we already handled the x-label with ax1
        ax2.set_ylim(0,120)
        # plt.title('Power flow during 1st simulated day', fontsize=18)
        fig.tight_layout()
    
        fig, ax1 = plt.subplots(figsize=(12,12))
    
        ln1 = ax1.plot(val.p_load[960:1440], 'orange', label='load')
        ln2 = ax1.plot(val.p_pv[960:1440], 'r', label='pv')
        ln3 = ax1.plot(val.p_battery_flow[960:1440], 'g', label='batt')
        ln4 = ax1.plot(val.p_grid_flow[960:1440], 'b', label='grid')
        ax2 = ax1.twinx()
        ln5 = ax2.plot(val.battery_SOC[960:1440], 'black', label='SOC')
        lns = ln1+ln2+ln3+ln4+ln5
        labs = [l.get_label() for l in lns]
        ax1.legend(lns, labs)
    
        ax1.grid()
        ax1.set_xlabel('Time', fontsize=14)
        ax1.set_ylabel('Power flow (kW)', fontsize=14)
        ax2.set_ylabel('Battery SOC', color='black', fontsize=14)  # we already handled the x-label with ax1
        ax2.set_ylim(0,120)
        # plt.title('Power flow during 1st simulated day', fontsize=18)
        fig.tight_layout()