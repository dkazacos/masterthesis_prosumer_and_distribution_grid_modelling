# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 10:05:26 2020

@author: Seta
"""

import os
import sys
import random
sys.path.append(os.getcwd()+'\\v0_2')
import pandapower.networks as nw
import pandapower as pp
import pandas as pd
import numpy as np
from v0_2.Prosumer import Prosumer

# ============================================================================
# Create NETWORK

net = pp.create_empty_network()
# Create buses
pp.create_bus(net, name='Bus ext grid', vn_kv=10., type='b')
pp.create_bus(net, name='Bus LV0', vn_kv=0.4, type='n')
for i in range(1, 6):
    pp.create_bus(net, name='Bus LV1.%s' % i, vn_kv=0.4, type='m')
for i in range(1, 5):
    pp.create_bus(net, name='Bus LV2.%s' % i, vn_kv=0.4, type='m')
pp.create_bus(net, name='Bus LV2.2.1', vn_kv=0.4, type='m')
pp.create_bus(net, name='Bus LV2.2.2', vn_kv=0.4, type='m')
# Create lines
for i in range(1,6):
    pp.create_line(net, from_bus=i, to_bus=i+1, length_km=0.08, std_type='NAYY 4x120 SE')
pp.create_line(net, from_bus=1, to_bus=7, length_km=0.12, std_type='NAYY 4x120 SE')
pp.create_line(net, from_bus=7, to_bus=8, length_km=0.12, std_type='NAYY 4x120 SE')
for i in range(8, 10):
    pp.create_line(net, from_bus=i, to_bus=i+1, length_km=0.12, std_type='15-AL1/3-ST1A 0.4')
pp.create_line(net, from_bus=8, to_bus=11, length_km=0.12, std_type='15-AL1/3-ST1A 0.4')
pp.create_line(net, from_bus=11, to_bus=12, length_km=0.12, std_type='15-AL1/3-ST1A 0.4')
# Create external grid
pp.create_ext_grid(net, bus=0, m_pu=1.03, va_degree=0, name='External grid',
                   s_sc_max_mva=10000, rx_max=0.1, rx_min=0.1)
# Create transformer
pp.create_transformer_from_parameters(net, hv_bus=0, lv_bus=1, sn_mva=.4,
                                      vn_hv_kv=10, vn_lv_kv=0.4, vkr_percent=1.325,
                                      vk_percent=4, pfe_kw=0.95, i0_percent=0.2375,
                                      tap_side="hv", tap_neutral=0, tap_min=-2,
                                      tap_max=2, tap_step_percent=2.5, tp_pos=0,
                                      shift_degree=150, name='MV-LV-Trafo')

# ============================================================================
# Create PROSUMERS
# Data preparation
# Import irradiance test data
irr = pd.read_csv(
                  filepath_or_buffer = 'data/1minIntSolrad-07-2006.csv',
                  sep                = ';',
                  skiprows           = 25,
                  parse_dates        = [[0,1]],
                  index_col          = 0,
                  )
# Import load_profile test data
load_data = pd.read_csv(
                        filepath_or_buffer = 'data/1MinIntSumProfiles-Apparent-2workingpeople.csv',
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

# Ceate neighborhood
neighborhood = {}
for b in net.bus.index[1:]:

    # Generate a variation of a prosumer load of +/- 30 %
    ft = random.randint(1,30)/100
    ld = load_demand*(1-ft)
    # Install a PV power around the magnitude of the peak demand of Prosumer X
    pk = np.max(ld)
    # stantiate a Prosumer X
    META = {}
    META['load_demand']         = ld
    META['pv_kw']               = pk*0.7
    META['battery_capacity']    = 3.5
    p = Prosumer(**META)
    # Store Prosumer X in Neighborhood dictionary
    neighborhood['Prosumer %s in %s' % (b, net.bus.name[b])] = p

# Create loads
for pr, ind in zip(neighborhood.keys(), net.bus.index[1:]):
    pp.create_load(net, bus=ind,
                   p_mw=neighborhood[pr].pv_kw/1000,
                   name=pr[:9+len(str(ind))])

# ============================================================================
# Run Net POWERFLOW
pp.runpp(net)
print(net.res_line)