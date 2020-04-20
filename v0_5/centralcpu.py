# -*- coding: utf-8 -*-
"""
Created on Tue Apr 14 20:21:57 2020

@author: Seta
"""

from v0_5.recorder import Recorder

class CPU(object):
    """
    CPU analyzes the state of the grid at a given point in time and
    reacts to prevent unwanted states of lines. Monitored variables
    supported by this class are the following:
        vm_pu : voltage of the buses in per-unit
        loading_percent: thermal overload of lines
        ext_grid.p_mw : slack power of the grid
    """
    def __init__(self):

        self.recorder = Recorder('overvoltage',
                                 'undervoltage',
                                 'thermal_overload',
                                 'slack_power',
                                 )

    def check_overvoltage(self, net):
        """
        CPU Recorder records 1, if overvoltage is found at any bus of
        any line, or 0, if no overvoltage is found
        """
        if not net.res_bus.query('vm_pu >= 1.03').vm_pu.any():
            self.recorder.record(overvoltage=0)
        else:
            self.recorder.record(overvoltage=1)

    def check_undervoltage(self, net):
        """
        CPU Recorder records 1, if undervoltage is found at any bus of
        any line, or 0, if no undervoltage is found
        """
        if not net.res_bus.query('vm_pu <= 0.97').vm_pu.any():
            self.recorder.record(undervoltage=0)
        else:
            self.recorder.record(undervoltage=1)

    def check_thermal_overload(self, net):
        """
        CPU Recorder records 1, if thermal overload is found at any line,
        or 0, if no thermal overload is found
        """
        if not net.res_line.query('loading_percent >= 0.8').loading_percent.any():
            self.recorder.record(thermal_overload=0)
        else:
            self.recorder.record(thermal_overload=1)

    def check_slack_bus_power(self, net):
        self.recorder.record(slack_power=0)

    def recursive_net_search(self, net, lines):
        """
        Down-stream search for lines attached to buses to which lines
        found with thermal overload feed

        net : pandapower net object

        lines: list
            list of lines initially found with thermal overload

        Return
            extenden lines list with children down-stream lines
        """
        buses = net.line.loc[lines, 'to_bus'].tolist()
        if not set(buses).intersection(net.line['from_bus']):
            pass
        else:
            line_set = [net.line.index[net.line['from_bus']==b] for b in buses]
            stop = len(lines)
            lines.extend([item for sublist in line_set for item in sublist if item not in lines])
            if len(lines) == stop:
                pass
            else:
                return self.recursive_net_search(net, lines)

    def risk_identifier(self, net, flags):
        """
        If any operational risk is identified in any line or bus,
        this function will return a dictionary with identified
        responsible buses
        
        This ditionary will be empty otherwise
        """

        risks = {}
        if flags['overvoltage']:
            buses = net.res_bus.query('vm_pu >= 1.03').vm_pu.index.tolist()
            ov_in_bus = net.bus.loc[buses, 'name'].tolist()
            risks['overvoltage'] = ov_in_bus
            # ov_bus_to_default = set(net.bus.index.tolist()).difference([*ov_in_bus])

        if flags['undervoltage']:
            buses = net.res_bus.query('vm_pu <= 0.97').vm_pu.index.tolist()
            uv_in_bus = net.bus.loc[buses, 'name'].tolist()
            risks['undervoltage'] = uv_in_bus
            # uv_bus_to_default = set(net.bus.index.tolist()).difference([*uv_in_bus])

        if flags['thermal_overload']:
            lines = net.res_line.query('loading_percent >= 80').loading_percent.index.tolist()
            # self.recursive_net_search(net, lines)
            buses = net.line.loc[lines, 'to_bus'].tolist()
            tho_due_to_buses = net.bus.loc[buses, 'name'].tolist()
            risks['thermal_overload'] = tho_due_to_buses
            # tho_bus_to_default = set(net.bus.index.tolist()).difference([*tho_due_to_buses])

        if flags['slack_power']:
            pass

        else:
            bus_with_risk = []
            for _, buses in risks.items():
                bus_with_risk.append(buses)
            prosumers_to_default = set(net.load.bus.tolist()).difference(*bus_with_risk)
            risks['to_default'] = net.bus.loc[prosumers_to_default, 'name'].tolist()

        return risks

    def prosumers_to_intervene(self, neighborhood, bus_names):
        """
        Returns a list of prosumers at the identified buses where
        riks operation is present
        """
        return list(set(neighborhood.keys()).intersection(set(bus_names)))

    def prosumer_persistent_behavior(self, counts):
        for risk, val in self.recorder.meta.keys():
            event = self.recorder.meta[risk][-1]
            access = counter(risk, event, lag)
            if access:
                pass
            else:
                self.recorder.meta[risk][-1] = 1

    def switch_behavior(self, risk, neighborhood, prosumers):
        """
        Commands each prosumer connected to the buses where risky operation
        has been found to switch their behavior in order to better operate
        the grid
        """
        if risk == 'overvoltage':
            for p in prosumers:
                neighborhood[p].battery_mode = 'self-consumption' # or 'buffer-grid' with min_max_SOC = (0, 80) or (0, 75) from beforehand. min_SOC=0 to allow full discharge of battery without penalizatin
                neighborhood[p].pv_strategy = 'curtailment' # avoid feed-in of active power
        elif risk == 'undervoltage':
            for p in prosumers:
                neighborhood[p].battery_mode = 'buffer-grid' # with min_max_SOC=(20, 80) or (25, 75) because we need to consume from grid or feed into it. Even 'battery-bypass'
                neighborhood[p].pv_strategy = 'self-consumption' # allow full feed-in if available
        elif risk == 'thermal_overload':
            for p in prosumers:
                neighborhood[p].battery_mode = 'self-consumption' # allow full charge/discharge without penalization because we need to reduce consumption from grid
                neighborhood[p].pv_strategy = 'curtailment' # avoid feed-in
                neighborhood[p].prosumer_profile = 'energy-saving' # back to default
        elif risk == 'to_default':
            for p in prosumers:
                neighborhood[p].battery_mode = 'self-consumption' # back to default
                neighborhood[p].pv_strategy = 'self-consumption' # back to default
                neighborhood[p].prosumer_profile = 'self-consumption' # back to default

    def check_net(self, net):
        """
        Returns a binary list of the las occurrence with 1 or 0 whether
        a certain operational risk is found or not
        """
        self.check_overvoltage(net)
        self.check_undervoltage(net)
        self.check_thermal_overload(net)
        self.check_slack_bus_power(net)

        return self.recorder.last_occurrence()

    # def to_default_behavior(self, net, risks):

    #     bus_with_risk = []
    #     for key, val in risks.items():
    #         bus_with_risk.append(val)
    #     prosumers_to_default = set(net.bus.index.tolist()).difference(*bus_with_risk)
    #     return list(prosumers_to_default)

    def control_prosumers(self, net, neighbodhood, bypass_control=False):
        """
        Main function to be called from the outside. This function allows
        the control of prosumers to happen
        """
        flags = self.check_net(net)
        if bypass_control:
            pass
        else:
            risks = self.risk_identifier(net, flags)
            for risk, prosumers in risks.items():
                # prosumers = self.prosumers_to_intervene(neighbodhood, val)
                self.switch_behavior(risk, neighbodhood, prosumers)
