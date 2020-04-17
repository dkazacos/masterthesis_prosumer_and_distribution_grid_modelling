# -*- coding: utf-8 -*-
"""
Created on Sat Feb 29 19:39:20 2020

@author: Seta
"""

import sys
sys.path.append('..')
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from Prosumer import Prosumer
from PVgen import PVgen
from Storage import BatterySimple, Battery
from utils.function_repo import parse_hours, timegrid

# ========================================================================
# MAIN
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
pvgen = PVgen(installed_pv = 2.1)
battery = BatterySimple(battery_capacity = 3.5,
                        initial_SOC = 75,
                        min_max_SOC = (20,80))
psimp = Prosumer(
                pvgen = pvgen,
                battery = battery,
                )

# batterycomplex = Battery(battery_capacity = 3.5,
#                         initial_SOC = 75,
#                         min_max_SOC = (20,80))
# psimp = Prosumer(
                # pvgen = pvgen,
                # battery = batterycomplex,
                # )

# psimp.run_static_sim(
#                   irrad_data = irrad_data,
#                   load_data = load_demand,
#                   )

timestep = timegrid(irrad_data)
for i, (irr, ld) in enumerate(zip(irrad_data, load_demand)):
    psimp.run_pflow(
                    irrad_data  = irr,
                    load_data   = ld,
                    timestep    = timestep,
                    timestamp   = load_demand.index[i],
                    )

# pphys.run_static_sim(
#                     irrad_data = irrad_data,
#                     )

prosumer_dict = {}
prosumer_dict['res_simp'] = psimp.get_prosumer_data()
prosumer_dict['res_simp'].set_index('timestamp', inplace=True)
# prosumer_dict['res_compl'] = psimp.get_cpu_data()

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