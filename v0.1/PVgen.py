# -*- coding: utf-8 -*-
"""
Created on Sat Feb 29 20:12:09 2020

@author: Seta
"""

import math
import decimal
import pandas as pd
import warnings

class PVgen(object):
    
    """
    PV installation is characterized by the following arguments

    Parameters
    ----------
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

    oda_t : float, default None
        outdoor air temperature data. Power output dependency on outdoor
        temperature is not yet defined.

    ----------
    Accepts combination of arguments to fully characterize a PV installation

        .. PV peak power installed (pv_kw) fully characterizes installation

        .. number of panels (num_panels) fully characterizes installation

        .. available roof area (roof_area) fully characterizes installation

    Returns
    -------
    float
        Power generation from PV installation at a given timestamp provided in
        production() method
    """

    def __init__(self,
                 pv_kw          = None,
                 num_panels     = None,
                 panel_peak_p   = 0.3,
                 pv_eff         = 0.18,
                 roof_area      = None,
                 pv_total_loss  = 0.0035,
                 module_area    = 1.96,
                 oda_t          = None,
                 ):

        self.pv_kw          = pv_kw
        self.num_panels     = num_panels
        self.panel_peak_p   = panel_peak_p
        self.pv_eff         = pv_eff
        self.roof_area      = roof_area
        self.pv_total_loss  = pv_total_loss
        self.module_area    = module_area
        self.oda_t          = oda_t
        if self.pvgen.pv_kw != self.pv_kw:
            self.pv_kw = self.pvgen.pv_kw
        self.meta           = {
                               'irr_sol'  : [],
                               # 'oda_t'    : [],
                               }
        if not self.pv_kw:
            if self.num_panels:
                self.pv_kw = self.num_panels * self.panel_peak_p
                if self.roof_area:
                    if self.num_panels * self.module_area > math.floor(self.roof_area / self.module_area):
                        raise AttributeError('Invalid number of PVgen panels: %s. Won´t fit in roof area: %s m2 for a module area of %s m2' % (self.num_panels, self.roof_area, self.module_area))
            elif self.roof_area and not self.num_panels:
                self.num_panels = math.floor(self.roof_area / self.module_area)
                self.pv_kw = self.num_panels * self.panel_peak_p
            else:
                warnings.warn('Missing args: see PVgen class documentation. Need pv_kw, num_panels or roof_area')
        elif self.pv_kw and not self.num_panels:
            if self.pv_kw < 0:
                raise AttributeError('PV installed power cannot be a negative number')
            if self.roof_area:
                if self.pv_kw / self.panel_peak_p * self.module_area > self.roof_area:
                    raise AttributeError('Invalid PVgen installed power. Not enough roof area for given module characteritics to yield %s kW. Reduce PV installed power or increase roof area' % self.pv_kw)
            if decimal.Decimal('%s' % self.pv_kw) % decimal.Decimal('%s' % self.panel_peak_p) != 0:
                self.num_panels = math.ceil(self.pv_kw / self.panel_peak_p)
                self.pv_kw = self.num_panels * self.panel_peak_p
                warnings.warn('Module characteristics require chosen PVgen installed power to be adjusted to %s kW. See class default args' % self.pv_kw)
            else:
                self.num_panels = self.pv_kw / self.panel_peak_p
        
    def get_installed_pv(self):
        """
        Returns the PV installed power in kW
        """
        return self.pv_kw
    
    def get_pv_sys_loss(self):
        """
        Returns the PV total power loss in per unit
        """
        return self.pv_total_loss
    
    def get_pv_data(self):
        """
        Returns pandas dataframe composed by object's meta dictionray of data
        """
        return pd.DataFrame(self.meta)
    
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
        p_sun_wh = irr_sol * self.module_area * self.num_panels
        p_sun_kw = p_sun_wh / timestep * 3.6
        if p_sun_kw > self.get_installed_pv():
            return self.get_installed_pv() * (1. - self.pv_total_loss)
        else:
            return p_sun_kw * (1. - self.pv_total_loss)