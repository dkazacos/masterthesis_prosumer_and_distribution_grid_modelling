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