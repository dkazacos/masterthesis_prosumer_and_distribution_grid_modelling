# -*- coding: utf-8 -*-
"""
Created on Wed Apr  8 20:44:40 2020

@author: Seta
"""


class SolarPanel(object):

    """
    Solar panel is fully characterized by its attributes:

        panel_peak_p : float, default 0.3
            rated power of a single solar panel in kW        

        module_area : float, default 1.96 m2
            area of a single solar panel
    
        pv_eff : float, default 0.18
            efficiency of single solar panel
    """

    def __init__(self, panel_peak_p=0.3, module_area=1.96, pv_efficiency=0.18):

        self.panel_peak_p   = panel_peak_p
        self.pv_efficiency  = pv_efficiency
        self.module_area    = module_area

    def get_panel_peak_p(self):
        return self.panel_peak_p

    def get_module_area(self):
        return self.module_area

    def get_panel_specs(self):
        print(' Panel peak power', self.panel_peak_p*1000, 'W\n',
              'Panel area', self.module_area, 'm2\n',
              'Panel efficiency', self.pv_efficiency*100, '%')

    def production(self, irradiance, timestep):
        """
        irradiance : float, default None
            irradiance is measured in Wh/m2 and is assumed to be global inclined

        timestep : int, default None
            time resolution of irradiation data passed for production in
            seconds

        Return
        --------
        float
            power production yielded by a single solar panel in kWh
        """
        p_sun_wh = irradiance * self.module_area
        p_sun_kw = p_sun_wh / timestep * 3.6
        if p_sun_kw > self.panel_peak_p:
            p_prod = self.panel_peak_p
        else:
            p_prod = p_sun_kw
        return p_prod