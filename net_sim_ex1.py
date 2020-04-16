# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 10:05:26 2020

@author: Seta
"""

from collections import defaultdict
import os
import sys
import random
sys.path.append(os.getcwd()+'\\v0_4')

import pandapower as pp
from pandapower import timeseries as ts
from pandapower import control
import pandas as pd
import numpy as np
import time

from v0_4.CPU import Prosumer
from v0_4.centralcpu import CPU
from Storage import BatterySimple, BatterySimple
from PVgen import PVgen
from utils.function_repo import parse_hours, timegrid

# ============================================================================
# Create NETWORK

def simple_net():
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
                       s_sc_max_mva=10, rx_max=0.1, rx_min=0.1)
    # Create transformer
    pp.create_transformer_from_parameters(net, hv_bus=0, lv_bus=1, sn_mva=.4,
                                          vn_hv_kv=10, vn_lv_kv=0.4, vkr_percent=1.325,
                                          vk_percent=4, pfe_kw=0.95, i0_percent=0.2375,
                                          tap_side="hv", tap_neutral=0, tap_min=-2,
                                          tap_max=2, tap_step_percent=2.5, tp_pos=0,
                                          shift_degree=150, name='MV-LV-Trafo')
    for ind in range(1,13):
        pp.create_load(net, bus=ind,
                        p_mw=0.0035,
                        name='Prosumer %s' % ind)
    return net

def import_data():
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
    # Convert 0..24:00 hours to 0..23:59
    parse_hours(irr)
    load_data.index = pd.to_datetime(load_data.index, dayfirst=True) + pd.Timedelta(minutes=1)
    load_demand     = load_data.iloc[:, 0]
    irrad_data      = irr.iloc[:, 3]
    irrad_data.index= pd.to_datetime(irrad_data.index) + pd.DateOffset(years=10)
    if any(',' in string for string in load_demand):
        load_demand = load_demand.str.replace(',', '.')
        load_demand = 30*pd.to_numeric(load_demand)

    return irrad_data, load_demand

def neighborhood(net):

    _, load_demand = import_data()
    neighborhood = {}
    for b in net.bus.index[1:]:

        # Randomly generate a variation of a prosumer pv peak within +/- 30 %
        ft = random.randint(1,30)/100
        ld = load_demand*(1-ft)
        # Install a PV power around the magnitude of the peak demand of Prosumer X
        pk = np.max(ld)
        # stantiate a Prosumer X
        pvgen   = PVgen(installed_pv = pk*0.7)
        battery = BatterySimple(battery_capacity = 3.5,
                                initial_SOC = 60,
                                min_max_SOC = (20,80))
        p = Prosumer(pvgen = pvgen, battery=battery)
        # Store Prosumer X in Neighborhood dictionary
        neighborhood['%s' % net.bus.name[b]] = p

    return neighborhood

# Initialize results storage
def create_output_writer(net, time_steps, output_dir):
    ow = ts.OutputWriter(net, time_steps, output_path=output_dir,
                         output_file_type=".xls", log_variables=list())
    # these variables are saved to the harddisk after / during the time series loop
    ow.log_variable('res_ext_grid', 'p_mw')
    # ow.log_variable('res_load', 'p_mw')
    ow.log_variable('res_bus', 'vm_pu')
    ow.log_variable('res_line', 'loading_percent')
    # ow.log_variable('res_line', 'i_ka')
    return ow

# ============================================================================
# RUN example
# Load data
irr, load = import_data()
# Extract timestep size
timestep = timegrid(load)
# create network
net = simple_net()
# create neighborhood
nh = neighborhood(net)
# create central CPU that monitors and commands prosumers
cpu = CPU()

now=time.time()
res = defaultdict(list)
# Run stepwise simulation extracting load and irradiation
for i, (ir, ld) in enumerate(zip(irr[:1230], load[:1230]*10)):
    # Instantiate a controller unit for each Prosumer's load
    for j, (key, val) in enumerate(nh.items()):
        d = pd.DataFrame(index=[0])
        # Randomly generate a variation of a prosumer load within +/- 30 %
        ld = ld*(1-random.randint(1,30)/1000)
        val.run_pflow(ir, ld, timestep, timestamp=irr[:1440].index[i])
        net.load.at[j, "p_mw"] = -val.recorder.meta['p_grid_flow'][-1]/1000
        # d[key] = -val.recorder.meta['p_grid_flow'][-1]/1000
        # ds = ts.DFData(d)
        # control.ConstControl(net, element='load',
        #                       element_index=[j],
        #                       variable='p_mw',  data_source=ds,
        #                       profile_name=[key])
        print("net_load",net.load.loc[j,"p_mw"], "pros_SOC", val.recorder.meta['battery_SOC'][-1])
    # Run power flow calculation at every timestep iteration
    # ow = create_output_writer(net,[], "E:/Temp")
    # ts.run_timeseries(net, verbose=False)
    pp.runpp(net)
    cpu.control_prosumers(net, nh)
    # Store line overload, voltage at buses and slack power balance
    res['Time'].append(irr.index[i])
    res['load'].append(net.load.p_mw.tolist())
    res['load_real'].append(load)
    res['th_overload'].append(net.res_line.loading_percent.tolist())
    res['vm_pu_bus'].append(net.res_bus.vm_pu.tolist())
    res['slack_p'].append(net.res_ext_grid.p_mw.tolist())
    # print('Time since beginning of simulation: ', time.time() - now)
results = pd.DataFrame(res)