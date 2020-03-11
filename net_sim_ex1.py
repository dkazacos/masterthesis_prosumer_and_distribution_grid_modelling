# -*- coding: utf-8 -*-
"""
Created on Mon Mar  9 10:05:26 2020

@author: Seta
"""

import sys
sys.path.append('..')
import pandapower.networks as nw
import pandapower as pp
from Prosumer import Prosumer

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
for i in range(9, 11):
    pp.create_line(net, from_bus=i, to_bus=i+1, length_km=0.12, std_type='15-AL1/3-ST1A 0.4')
pp.create_line(net, from_bus=9, to_bus=11, length_km=0.12, std_type='15-AL1/3-ST1A 0.4')
pp.create_line(net, from_bus=11, to_bus=12, length_km=0.12, std_type='15-AL1/3-ST1A 0.4')
# Create external grid
pp.create_ext_grid(net, bus=0, m_pu=1.03, va_degree=0, name='External grid',
                   s_sc_max_mva=10000, rx_max=0.1, rx_min=0.1)
# Create transformer
pp.create_transformer(net, from_bus=0)