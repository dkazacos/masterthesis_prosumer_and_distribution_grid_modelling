# -*- coding: utf-8 -*-
"""
Created on Sat Feb 29 20:12:09 2020

@author: Seta
"""

import math
import decimal
import warnings
from recorder import Recorder
from panels import SolarPanel

class PVgen(SolarPanel):
    """
    """
    strategy = 'self-consumption' # also: 'curtailment'

    def __init__(self,
                 installed_pv   = None,
                 num_panels     = None,
                 pv_total_loss  = 0.0035,
                 ):

        super().__init__()
        self.panel_peak_p   = super().get_panel_peak_p()
        self.module_area    = super().get_module_area()
        self.installed_pv   = installed_pv
        self.num_panels     = num_panels
        self.pv_total_loss  = pv_total_loss
        self.recorder       = Recorder(
                                        'p_prod',
                                        'irr_sol',
                                        'p_curtail',
                                        )

    def get_pv_data(self):
        """
        Returns pandas dataframe composed by object's meta dictionray of data
        """
        return self.recorder.get_data()

    def get_pv_sys_loss(self):
        """
        Returns the PV total power loss in per unit
        """
        return self.pv_total_loss

    def set_installed_pv_power(self, installed_pv):
        """
        init installed pv power with desired value installed pv in kW
        Careful: pv installed power obeys the limitations of the panel
        characteristics. Make sure to set a power that is multiple of
        panel_peak_p attribute
        """
        self.installed_pv = installed_pv


    def _readjust_pv_kw(self, verbose=False):
        if verbose:
            warnings.warn('Module characteristics require chosen PVgen ' +
                          'installed power to be adjusted to ' +
                          '%s kW. See class default args' % self.installed_pv)
        self.installed_pv = self.num_panels * self.panel_peak_p

    def production(self, irr_sol, timestep):
        """
        A simple model of the PV power pordocution is executed by this function

        Parameters
        ----------
        irr_sol : float
            Irradiance characterizes the amount of power output that can be
            generated by the PV installation. It is expected to receive an
            irradiance in Wh/m2 for a time interval

        Returns
        -------
        float
            Power generation from PV installation at a given timestamp

        """

        if self.installed_pv and not self.num_panels:
            if self.installed_pv < 0:
                raise AttributeError('PV installed power cannot be a negative number')
            if decimal.Decimal('%s' % self.installed_pv) % decimal.Decimal('%s' % self.panel_peak_p) != 0:
                self.num_panels = math.ceil(self.installed_pv / self.panel_peak_p)
                self._readjust_pv_kw()
            else:
                self.num_panels = self.installed_pv / self.panel_peak_p

        elif self.installed_pv and self.num_panels:
            if self.num_panels * self.panel_peak_p != self.installed_pv:
                raise AttributeError('PV installed power and number of panels' +
                                     'do not match for given panel characteristics')

        p_yield = super(PVgen, self).production(irr_sol, timestep)
        installation_power_yield = self.num_panels * p_yield

        self.recorder.record(irr_sol    = irr_sol,
                              p_prod    = installation_power_yield)
        return installation_power_yield * (1 - self.pv_total_loss)
