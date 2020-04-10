# -*- coding: utf-8 -*-
"""
Created on Fri Feb 21 23:20:35 2020

@author: Seta
"""

import pandas as pd
import numpy as np
from scipy.integrate import odeint
import warnings
from recorder import Recorder

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

    min_max_SOC : tuple, default None
        buffer interval for grid feed-in and supply simultaneity control in %

    Returns
    ----------

    """

    state   = None
    mode  = 'self-consumption'
    p_kw    = None

    def __init__(self,
                 battery_capacity   = 7.5,
                 initial_SOC        = 100,
                 min_max_SOC        = (0, 100),
                 ):

        self.battery_capacity   = battery_capacity      # capacity of battery [kWh]
        self.initial_SOC        = initial_SOC           # initial state of charge [%]
        self.min_max_SOC        = min_max_SOC           # buffer SOC interval
        self.recorder           = Recorder(
                                           'P',         # dictionary of data
                                           'p_reject',  # rejected by battery
                                           'battery_SOC', # state of charge
                                           'log',       # occurrences
                                           )
        if self.battery_capacity < 0:
            raise AttributeError('Battery capacity cannot be a negative number')

    def get_battery_soc(self):
        """
        Returns the battery state of charge in %
        """
        if not self.recorder.meta['battery_SOC']:
            return self.initial_SOC
        else:
            return self.recorder.meta['battery_SOC'][-1]

    def get_battery_state(self):
        """
        Returns the current state of a battery instance as a string log
        """
        if self.get_battery_soc() == 100:
            self.state = 'Fully charged'
            return self.state
        elif self.get_battery_soc() == 0:
            self.state = 'Depleted'
            return self.state
        elif (self.get_battery_soc()>0) and (self.get_battery_soc()<100):
            self.state = 'Operational'
            return self.state

    def set_battery_mode(self, mode):
        self.mode = mode

    def get_battery_data(self):
        """
        Returns a pandas dataframe composed by object's recorder meta dictionary
        """
        return self.recorder.get_data()

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

    def bms(self, h, c):
        """
        Battery Management System (BMS). Dictates the acceptance of
        rejection of power flow by the battery
        """
        st  = self.get_battery_state()
        soc = self.get_battery_soc()
        p   = self.p_kw
        if p < 0:
            if st == 'Fully charged':
                Q       = c*soc/100
                p_acc   = 0
                p_rej   = -p
            elif st in ['Operational', 'Depleted']:
                if self.mode == 'buffer-grid':
                    upper_boundary = self.min_max_SOC[1]
                    if soc >= upper_boundary:
                        Q       = c*soc/100 - p*h*(100-soc)/(100-upper_boundary)
                        p_acc   = p*(100-soc)/(100-upper_boundary)
                        p_rej   = -p*(1- (100-soc)/(100-upper_boundary))
                    else:
                        Q       = c*soc/100 - p*h
                        p_acc   = p
                        p_rej   = 0
                elif self.mode == 'self-consumption':
                    Q       = c*soc/100 - p*h
                    p_acc   = p
                    p_rej   = 0
        elif p > 0:
            if st == 'Depleted':
                Q       = c*soc/100
                p_acc   = 0
                p_rej   = -p
            elif st in ['Operational', 'Fully charged']:
                if self.mode == 'buffer-grid':
                    lower_boundary = self.min_max_SOC[0]
                    if soc <= lower_boundary:
                        Q       = c*soc/100 - p*h*(soc/lower_boundary)
                        p_acc   = p*(soc/lower_boundary)
                        p_rej   = -p*(1-soc/lower_boundary)
                    else:
                        Q       = c*soc/100 - p*h
                        p_acc   = p
                        p_rej   = 0
                elif self.mode == 'self-consumption':
                    Q       = c*soc/100 - p*h
                    p_acc   = p
                    p_rej   = 0
        elif p == 0:
            Q       = c*soc/100
            p_acc   = 0
            p_rej   = 0

        return p_acc, p_rej, soc, Q

    def process(self, p_kw, timestep):

        """
        Populates an object's recorder meta dictionary with data comming from
        the power flow through the battery after BMS filtering
        """
        self.p_kw               = p_kw
        h                       = timestep/3600
        c                       = self.battery_capacity
        p_acc, p_rej, soc, Q    = self.bms(h, c)

        if p_acc > 0: # discharge battery
            if Q < 0:
                self.state = 'Depleted'
                self.recorder.record(
                                    p_reject    = Q/h,      # rejected negative power (negative for grid)
                                    P           = (c*soc/100)/h,
                                    battery_SOC = 0,
                                    log         = 'discharged, depleted',
                                    )
            elif Q >= 0:
                self.state = 'Operational'
                self.recorder.record(
                                    p_reject    = p_rej,    # rejected negative power (negative for grid)
                                    P           = p_acc,
                                    battery_SOC = Q/c*100,
                                    log         = 'discharging',
                                    )
        elif p_acc < 0: # charge battery
            if Q > c:
                self.state = 'Fully charged'
                self.recorder.record(
                                    p_reject    = (Q-c)/h,          # rejected positive power (positive for grid)
                                    P           = -c*(1-soc/100)/h, # accepted negative power (charge)
                                    battery_SOC = 100,
                                    log         = 'charged, fully charged',
                                    )
            elif Q <= c:
                self.state = 'Operational'
                self.recorder.record(
                                    p_reject    = p_rej,      # rejected positive power (positive for grid)
                                    P           = p_acc,      # accepted negative power (charge)
                                    battery_SOC = Q/c*100,
                                    log         = 'charging',
                                    )
        elif not p_acc: # no flow in/out battery
            self.recorder.record(
                                p_reject    = p_rej,      # rejected positive power (positive for grid)
                                P           = p_acc,      # accepted negative power (charge)
                                battery_SOC = soc,
                                log         = 'No power flow through battery',
                                )

class Battery(object):

    state       = 'Stand-by'
    mode      = 'self-consumption'
    overload    = False # boolean
    p_kw        = None  # float

    def __init__(self, battery_capacity=7.5, initial_SOC=100, min_max_SOC=(0,100),
                 cn=2.55, vn=3.7, dco=3.0, cco=4.2, max_c_rate=10):

        """
        Default properties of battery cell: Li-ion CGR18650E Panasonic

        """

        self.battery_capacity   = battery_capacity  # Capacity of battery [kWh]
        self.initial_SOC        = initial_SOC       # initial state of charge [%]
        self.min_max_SOC        = min_max_SOC       # interval for buffer-grid strategy [%]
        self.cn                 = cn                # nominal capacity of Li.ion cell [Ah]
        self.vn                 = vn                # nominal voltage of single [V]
        self.dco                = dco               # discharge cut-off [V]
        self.cco                = cco               # charge cut-off [V]
        self.max_c_rate         = max_c_rate        # determines max allowed current
        self.recorder           = Recorder(
                                    'P',            # Store Power accepted by battery [kW]
                                    'p_reject',     # Store Power rejected by battery [kW]
                                    'Q',            # Store charge of cell [Ah]
                                    'V1',           # Store voltage of RC-1st of cell [V]
                                    'V2',           # Store voltage of RC-2nd of cell [V]
                                    'Vcell',        # Store cell voltage [V]
                                    'battery_SOC',  # Store cell SOC [%]
                                    )
        
        self.ncells = self.battery_capacity/(self.cn*self.vn)*1000 # number of cells in battery pack

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
        if not self.recorder.meta['battery_SOC']:
            return self.initial_SOC
        else:
            return self.recorder.meta['battery_SOC'][-1]

    def get_battery_state(self):
        if self.get_battery_soc() == 100:
            self.state = 'Fully charged'
            return self.state
        elif self.get_battery_soc() == 0:
            self.state = 'Depleted'
            return self.state
        elif (self.get_battery_soc() > 0) and (self.get_battery_soc() < 100):
            if self.state == 'Stand-by':
                return self.state
            else:
                self.state = 'Operational'
                return self.state

    def set_battery_mode(self, mode):
        self.mode = mode

    def get_battery_current_mode(self):
        return self.mode

    def get_battery_cell_capacity(self):
        return self.cn

    def get_battery_cell_cut_off_charge(self):
        return self.cco

    def get_battery_cell_cut_off_discharge(self):
        return self.dco

    def get_battery_capacity(self):
        return self.battery_capacity

    def set_battery_capacity(self, c):
        """
        init battery capacity with desired value c in kWh
        """
        self.battery_capacity = c

    def get_battery_data(self):
        return self.recorder.get_data()

    def get_battery_number_of_li_ion_cells(self):
        if not isinstance(self.ncells, int):
            warnings.warn('Number of cells is an approximation. Chosen battery ' +
                          'capacity is inconsistent with number of cells since ' +
                          'number of cells needs to be an integer. True number ' +
                          'of cells is %s' % self.ncells)
        return np.ceil(self.ncells)

    def bms(self, v_cell, p_w, Q):
        """
        Battery Management System. Defines safety operation of battery
        charge and discharge

        p_w (float):   power demand/supply. External mode
        v_cell (float): cell voltage

        Returns cell active power In/Out
        """
        num_cells   = self.ncells
        st          = self.get_battery_state()
        soc         = Q/(self.cn * 36)
        if p_w/num_cells < 0:           # charge battery p < 0
            if st == 'Fully charged':
                p_acc = 0
                p_rej = -p_w
            elif st in ['Operational', 'Depleted', 'Stand-by']:
                self.state = 'Operational'
                if self.mode == 'buffer-grid':
                    upper_boundary = self.min_max_SOC[1]
                    if soc >= upper_boundary and soc < 100:
                        p_acc = p_w/num_cells * (100-soc)/(100-upper_boundary)
                        p_rej = -p_w/num_cells * (1-(100-soc)/(100-upper_boundary))
                    elif soc >= 100:
                        self.state = 'Fully charged'
                        p_acc = 0
                        p_rej = -p_w
                    else:
                        p_acc = p_w/num_cells
                        p_rej = 0   
                elif self.mode == 'self-consumption':
                    if soc < 100:
                        p_acc = p_w/num_cells
                        p_rej = 0
                    elif soc >= 100:
                        self.state = 'Fully charged'
                        p_acc = 0
                        p_rej = -p_w
        elif p_w/num_cells > 0:         # discharge battery p > 0
            if st == 'Depleted':
                p_acc = 0
                p_rej = -p_w
            elif st in ['Operational', 'Fully charged', 'Stand-by']:
                self.state = 'Operational'
                if self.mode == 'buffer-grid':
                    lower_boundary = self.min_max_SOC[0]
                    if soc <= lower_boundary and soc > 0:
                        p_acc = p_w/num_cells * (soc/lower_boundary)
                        p_rej = -p_w/num_cells * (1-soc/lower_boundary)
                    elif soc <= 0:
                        self.state = 'Depleted'
                        p_acc = 0
                        p_rej = -p_w
                    else:
                        p_acc = p_w/num_cells
                        p_rej = 0
                elif self.mode == 'self-consumption':
                    if soc > 0:
                        p_acc = p_w/num_cells
                        p_rej = 0
                    elif soc <= 0:
                        self.state = 'Depleted'
                        p_acc = 0
                        p_rej = -p_w
        elif p_w/num_cells == 0:
            self.state = 'Stand-by'
            p_acc = 0
            p_rej = 0

        return p_acc, p_rej

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

        if not self.recorder.meta['battery_SOC']:
            Qo     = self.cn*self.get_battery_soc()/100 * 3600      # initial condition for Q
            v_cell = self.cco
        else:
            Qo     = self.recorder.meta['Q'][-1]
        if self.state == 'Stand-by':
            v1o    = 0                   # initial condition for V1
            v2o    = 0                   # initial condition for V2
            if not self.recorder.meta['battery_SOC']:
                v_cell = self.cco - (1.2 - Qo/(self.cn * 3600))
            else:
                v_cell = self.meta['Vcell'][-1]
        else:
            v1o    = self.recorder.meta['V1'][-1] # initial condition for V1
            v2o    = self.recorder.meta['V2'][-1] # initial condition for V2
            v_cell = self.recorder.meta['Vcell'][-1]

        p_w             = p_kw*1000
        p_acc, p_rej    = self.bms(v_cell, p_w, Qo)
        icell           = self.icell(p_acc, v_cell)
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
        self.recorder.record(P              = sec/timestep*p_acc*self.ncells/1000,
                             p_reject       = p_acc/1000*(1-sec/timestep) + p_rej/1000,
                             Q              = Qt[-1],
                             V1             = v1t[-1],
                             V2             = v2t[-1],
                             Vcell          = v_cell[-1],
                             battery_SOC    = soct[-1]*100,
                            )