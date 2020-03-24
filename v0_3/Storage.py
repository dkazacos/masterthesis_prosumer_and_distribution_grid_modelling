# -*- coding: utf-8 -*-
"""
Created on Fri Feb 21 23:20:35 2020

@author: Seta
"""

import pandas as pd
import numpy as np
from scipy.integrate import odeint

class BatterySimple(object):
    """
    Linear behavior of charge and discharge of a battery. No
    physical process is considered in this model. Battery has
    a capacity that dictates power In/Out behavior

    Parameters
    ----------
    battery_capacity : float, default 7.5
        capacity of the battery in kWh

    initial_SOC : float, default 100
        initial state of charge of battery at beginning of simulation
        in percentage

    Returns
    ----------

    """

    state   = 'Fully charged'
    signal  = 'self-consumption'
    p_kw    = None

    def __init__(self,
                 battery_capacity   = 7.5,
                 initial_SOC        = 100,
                 ):

        self.battery_capacity   = battery_capacity      # capacity of battery [kWh]
        self.initial_SOC        = initial_SOC           # initial state of charge [%]
        self.meta               = {
                                   'P'              : [],   # dictionary of data
                                   'p_reject'       : [],   # rejected by battery
                                   'battery_SOC'    : [],   # state of charge
                                   'log'            : [],   # occurrences
                                   }
        if self.battery_capacity < 0:
            raise AttributeError('Battery capacity cannot be a negative number')

    def get_battery_soc(self):
        """
        Returns the battery state of charge in %
        """
        if len(self.meta['battery_SOC']) == 0:
            return self.initial_SOC
        else:
            return self.meta['battery_SOC'][-1]

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

    def set_battery_capacity(self, c):
        """
        init battery capacity with desired value c in kWh
        """
        self.battery_capacity = c

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
            if len(self.meta['battery_SOC']) == 0:
                Q = c*self.get_battery_soc()/100 - p*h
            else:
                Q = c*self.meta['battery_SOC'][-1]/100 - p*h
            if Q < 0:
                self.state = 'Depleted'
                self.meta['p_reject'].append(Q/h)   # rejected negative power (negative for grid)
                if len(self.meta['battery_SOC']) == 0:
                    self.meta['P'].append(c/h)      # accepted positive power (discharge)
                else:
                    self.meta['P'].append((c*self.meta['battery_SOC'][-1]/100)/h)
                self.meta['battery_SOC'].append(0)
                self.meta['log'].append('discharged, depleted')
            elif Q >= 0:
                self.state = 'Operational'
                self.meta['p_reject'].append(0)
                self.meta['P'].append(p)
                self.meta['battery_SOC'].append(Q/c*100)
                self.meta['log'].append('discharging')

        elif p < 0: # charge battery
            if len(self.meta['battery_SOC']) == 0:
                Q = c*self.get_battery_soc()/100 - p*h
            else:
                Q = c*self.meta['battery_SOC'][-1]/100 - p*h
            if Q > c:
                self.state = 'Fully charged'
                self.meta['p_reject'].append((Q-c)/h)                       # rejected positive power (positive for grid)
                self.meta['P'].append(-c*(1-self.meta['battery_SOC'][-1]/100)/h)    # accepted negative power (charge)
                self.meta['battery_SOC'].append(100)
                self.meta['log'].append('charged, fully charged')
            elif Q <= c:
                self.state = 'Operational'
                self.meta['p_reject'].append(0)
                self.meta['P'].append(p)
                self.meta['battery_SOC'].append(Q/c*100)
                self.meta['log'].append('charging')

        elif p == 0: # no flow in/out battery
            if st == 'Fully charged':
                self.meta['battery_SOC'].append(100)
                self.meta['p_reject'].append(-p_kw)                         # rejected at charging (positive for grid)
            elif st == 'Depleted':
                self.meta['battery_SOC'].append(0)
                self.meta['p_reject'].append(-p_kw)                         # rejected at discharging (negative for grid)
            elif st == 'Operational':
                if len(self.meta['battery_SOC']) == 0:
                    self.meta['battery_SOC'].append(100)
                else:
                    self.meta['battery_SOC'].append(self.meta['battery_SOC'][-1])
            self.meta['P'].append(p)
            self.meta['log'].append('No power flow through battery')

class Battery(object):

    state       = 'Stand-by'
    signal      = 'self-consumption'
    overload    = False
    p_kw        = None

    def __init__(self, ncells=1000, cn=2.55, initial_SOC=100, vn=3.7, dco=3.0, cco=4.2, max_c_rate=10):

        """
        Default properties of battery cell: Li-ion CGR18650E Panasonic

        Hint: Initial state of charge = 100%
        """

        # self.p_kw         = p_kw          # power exchange [kW]
        self.ncells         = ncells        # number of cells in battery pack
        self.cn             = cn            # nominal capacity of Li.ion cell [Ah]
        self.initial_SOC    = initial_SOC   # initial state of charge [%]
        self.vn             = vn            # nominal voltage of single [V]
        self.dco            = dco           # discharge cut-off [V]
        self.cco            = cco           # charge cut-off [V]
        self.max_c_rate     = max_c_rate    # determines max allowed current
        self.meta           = {'P'              : [], # Store Power accepted by battery [kW]
                               'p_reject'       : [], # Store Power rejected by battery [kW]
                               'Q'              : [], # Store charge of cell [Ah]
                               'V1'             : [], # Store voltage of RC-1st of cell [V]
                               'V2'             : [], # Store voltage of RC-2nd of cell [V]
                               'Vcell'          : [], # Store cell voltage [V]
                               'battery_SOC'    : [], # Store cell SOC [%]
                               }
        # self.signal                = signal    # resembles signals from outside

    # =========================================================================

    # @property
    # def cn(self):
    #     return self._nominal_cell_capacity
    # @cn.setter
    # def cn(self, capacity):
    #     self._nominal_cell_capacity = capacity

    # @property
    # def vn(self):
    #     return self._nominal_cell_voltage
    # @vn.setter
    # def vn(self, voltage):
    #     self._nominal_cell_voltage = voltage

    # @property
    # def dco(self):
    #     return self._discharge_cov
    # @dco.setter
    # def dco(self, dicoff):
    #     self._discharge_cov = dicoff

    # @property
    # def cco(self):
    #     return self._charge_cov
    # @cco.setter
    # def cco(self,chcoff):
    #     self._charge_cov = chcoff

    # =========================================================================

    def get_battery_soc(self):
        if len(self.meta['battery_SOC']) == 0:
            return self.initial_SOC # TODO! Try include parameter for user on this topic
        else:
            return self.meta['battery_SOC'][-1]

    def get_battery_state(self):
        return self.state

    def get_battery_capacity(self):
        return self.cn

    def get_battery_ccov(self):
        return self.cco

    def get_battery_dcov(self):
        return self.dco

    def get_battery_rated_energy_wh(self):
        return self.cn*self.vn*self.ncells

    def get_battery_data(self):
        return pd.DataFrame(self.meta)

    def get_battery_ncells(self):
        return self.ncells

    def bms(self, v_cell, p_w):
        """
        Battery Management System. Defines safety operation of battery
        charge and discharge

        p_w (float):   power demand/supply. External signal
        v_cell (float): cell voltage

        Returns cell active power In/Out
        """

        if p_w/self.ncells < 0:
            if v_cell < self.cco:
                self.state = 'Operational'
                return p_w/self.ncells
            elif v_cell >= self.cco:
                self.state = 'Fully charged'
                # TODO! place-holder for switch
                return 0

        elif p_w/self.ncells > 0:
            if v_cell > self.dco:
                self.state = 'Operational'
                return p_w/self.ncells
            elif v_cell <= self.dco:
                self.state = 'Depleted'
                # TODO! place-holder for switch
                return 0
        elif p_w == 0:
            self.state = 'Stand-by'
            return 0

    def icell(self, p_i, v_cell):
        """
        Icell < 0 for charge of cell
        Icell > 0 for discharge of cell

        p_i (float):    cell active power In/Out
        v_cell (float): cell voltage
        """

        if self.state == 'Operational':
            icell = p_i/v_cell
            if icell > self.cn * self.max_c_rate:
                self.overload   = True
                self.state      = 'Stand-by'
                return 0
            elif icell < -self.cn * self.max_c_rate:
                self.overload   = True
                self.state      = 'Stand-by'
                return 0
            else:
                self.overload   = False
                return icell
        else:
            return 0

    def cell_voltage(self, y, t, icell):
        """
        Voltage cell and SOC is calculated as a result of a system of equations
        as proposed by the equivalent circuit model according to XX

        Returns cell voltage and SOC at time t 
        -------
        None.

        """

        # CONSTANT PARAMETERS
        # Two RC elements (parallel connection of resistor and capacitor):
        # represent electrochemical reactions in each electrode of the cell
        r1 = 0.078   # Resistance of first RC element [Ohm]
        r2 = 0.078   # Resistance of second RC element [Ohm]
        c1 = 2       # Capacity of first RC element [Ah]
        c2 = 2       # Capacity of second RC element [Ah]

        # Vector of differentiable variables
        Q, v1, v2, = y

        # derivative of the vector y over time, which is the derivative 
        # of each element over time (differential equations)
        dydt = [
            - icell,                     # dQ/dt
            1/c1 * (icell - v1/r1) ,     # dV1/dt
            1/c2 * (icell - v2/r2) ,     # dV1/dt
        ]

        return dydt

    def process(self, p_kw, timestep):

        """
        timestep is needed in seconds -> timesteps of more than 1 hour
        may hinder the model of the physical process
        """

        self.p_kw = p_kw
        if p_kw == 0:
            self.state = 'Stand-by'
        rs = 0.078          # Serial resistance [Ohm]: ohmic resistance of cell
        t  = np.linspace(1, timestep, timestep)

        if len(self.meta['battery_SOC']) == 0:
            Qo     = self.cn*self.get_battery_soc()/100 * 3600      # initial condition for Q
            v_cell = self.cco
        else:
            Qo     = self.meta['Q'][-1]
        if self.state == 'Stand-by':
            v1o    = 0                   # initial condition for V1
            v2o    = 0                   # initial condition for V2
            if len(self.meta['battery_SOC']) > 0:
                v_cell = self.cco - (1.2 - Qo/(self.cn * 3600))
        else:
            v1o    = self.meta['V1'][-1] # initial condition for V1
            v2o    = self.meta['V2'][-1] # initial condition for V2
            v_cell = self.meta['Vcell'][-1]

        p_w             = p_kw*1000
        p_i             = self.bms(v_cell, p_w)
        icell           = self.icell(p_i, v_cell)
        y0              = Qo, v1o, v2o
        args            = (icell,)
        sol             = odeint(self.cell_voltage, y0, t, args)
        Qt, v1t, v2t    = sol[:,0], sol[:,1], sol[:,2]
        soct            = Qt / (self.cn * 3600)
        vs              = icell * rs
        if self.state == 'Operational':
            vot             = self.cco - (1.2 - soct)
            v_cell          = vot - v1t - v2t - vs
        else:
            v_cell      = [v_cell]
        if self.state in ['Fully charged', 'Depleted'] or self.overload:
            sec         = 0
        else:
            sec         = timestep

        if np.max(soct) > 1.:
            sec     = [i for (i,j) in enumerate(soct) if j > 1.][0]
            v_cell  = [self.cco]
            Qt      = [self.cn*3600]
            v1t     = [0]
            v2t     = [0]
            soct    = [1.]
        elif np.min(soct) < 0.:
            sec     = [i for (i,j) in enumerate(soct) if j < 0.][0]
            v_cell  = [self.dco]
            Qt      = [0]
            v1t     = [0]
            v2t     = [0]
            soct    = [0.]
        # Store data
        self.meta['P'].append(sec/timestep*p_kw)
        self.meta['p_reject'].append(-p_kw*(1-sec/timestep))
        self.meta['Q'].append(Qt[-1])
        self.meta['V1'].append(v1t[-1])
        self.meta['V2'].append(v2t[-1])
        self.meta['Vcell'].append(v_cell[-1])
        self.meta['battery_SOC'].append(soct[-1]*100)