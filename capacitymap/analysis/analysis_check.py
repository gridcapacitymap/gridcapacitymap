# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to Grid Capacity Map

"""
This file contains the function used to analyse the network. Rely heavily on powerflows.
"""

import pandapower as pp
from capacitymap.controllers.controller_functions import reset_all_controllers


def check_violations(net, run_control = False, vmax=1.1, vmin=0.9, max_line_loading=100., max_trafo_loading=100., p_lim=1000.):
    '''

    Parameters
    ----------
    net : A pandapower network
    include_ctr: bool, include controllers in power flow
    vmax : Upper voltage limit to check. The default is 1.05.
    vmin : Lower voltage limit to check. The default is 0.95.
    max_line_loading : Max line loading limit to check. The default is 100.
    max_trafo_loading : Max trafo loading limit to check. The default is 100.
    p_lim : Max injected power in ext_grid. Default 1000.

    Returns which limits have been broken
    -------
    upper_voltage : True or False
    lower_voltage : True or False
    line_loading : True or False
    trafo_loading : True or False
    ext_limit : True or False
    unsupplied: True or False
    not_converged: True or False

    '''
    check_violations.counter+=1
    upper_voltage = False
    lower_voltage = False
    line_loading = False
    trafo_loading = False
    ext_limit = False
    unsupplied = False
    not_converged = False
    violation_exp = [None] * 7
    try:
        pp.runpp(net,run_control=run_control)
        if net.res_bus.vm_pu.max() > vmax:
            upper_voltage = True
            violation_exp[0] = [x for x in net.bus.name[net.res_bus.vm_pu > vmax]]
        if net.res_bus.vm_pu.min() < vmin:
            lower_voltage = True
            violation_exp[1] = [x for x in net.bus.name[net.res_bus.vm_pu < vmin]]
        if net.res_line.loading_percent.max() > max_line_loading:
            line_loading = True
            violation_exp[2] = [x for x in net.line.index[net.res_line.loading_percent > max_line_loading]]#'Line ' + ", ".join() + ' overloaded'
        if net.res_trafo.loading_percent.max() > max_trafo_loading:
            trafo_loading = True
            violation_exp[3] = [x.replace("'",'').replace(' ','') for x in net.trafo.name[net.res_trafo.loading_percent > max_trafo_loading]]#'Trafo ' + ", ".join() + ' overloaded'
        if (net.res_ext_grid.p_mw > p_lim).any():
            ext_limit = True
            violation_exp[4] = 'Ext grid subscription overloaded'

        if (net.res_bus.loc[net.load.bus].isnull().values.any()):
            unsupplied = True
            df = net.res_bus.loc[net.load.bus.unique()]
            violation_exp[5] = [x for x in net.bus.name.loc[df['vm_pu'].index[df['vm_pu'].apply(np.isnan)]]]#'Load bus ' + + ' not supplied.'

    except:
        not_converged = True
        violation_exp[6] = True
    #print(upper_voltage, lower_voltage, line_loading, trafo_loading, ext_limit, unsupplied,not_converged)
    return (upper_voltage, lower_voltage, line_loading, trafo_loading, ext_limit, unsupplied,
            not_converged), violation_exp

def contingency_test(net, run_control = False, vmax=1.12, vmin=0.88, max_line_loading=120., max_trafo_loading=120., p_lim=1000., contingency_scenario = [[],[]]):
    '''
    Parameters
    ----------
    net : A pandapower network
    run_control: bool, include controllers in power flow
    vmax : Upper voltage limit to check. The default is 1.05.
    vmin : Lower voltage limit to check. The default is 0.95.
    max_line_loading : Max line loading limit to check. The default is 100.
    max_trafo_loading : Max trafo loading limit to check. The default is 100.
    p_lim : Max injected power in ext_grid. Default 1000.

    Returns list of lines indecies, when these lines or trafos are 
    out-of-service one or more checks fail
    -------------
    critical_lines: list of critical lines
    critical_trafos: list of critical trafo
    '''
    line_to_test = contingency_scenario[0]
    trafo_to_test = contingency_scenario[1]
    critical_lines = []
    critical_trafos = []
    for line_id in line_to_test:
        if net.line.loc[line_id, 'in_service']:
            net.line.loc[line_id, 'in_service'] = False
            check,_ = check_violations(net, run_control = run_control, vmax=vmax, vmin=vmin, max_line_loading=max_line_loading, max_trafo_loading=max_trafo_loading, p_lim=p_lim)
            
            if True in check:
                critical_lines.append(line_id)
            net.line.loc[line_id, 'in_service'] = True
            #Restore all controlers to inital state
            reset_all_controllers(net)

    for trafo_id in trafo_to_test:
        if net.trafo.loc[trafo_id, 'in_service']:
            net.trafo.loc[trafo_id, 'in_service'] = False
            
            check,_ = check_violations(net, run_control = run_control, vmax=vmax, vmin=vmin, max_line_loading=max_line_loading, max_trafo_loading=max_trafo_loading, p_lim=p_lim)
            
            if True in check:
                critical_trafos.append(trafo_id)
            net.trafo.loc[trafo_id, 'in_service'] = True
            #Restore all controlers to inital state
            reset_all_controllers(net)
    
    return critical_lines, critical_trafos

def simple_contingency_test(net, run_control = False, vmax=1.12, vmin=0.88, max_line_loading=120., max_trafo_loading=120., p_lim=1000., contingency_scenario = [[],[]]):
    '''
    Parameters
    ----------
    net : A pandapower network
    include_ctr: bool, include controllers in power flow
    vmax : Upper voltage limit to check. The default is 1.05.
    vmin : Lower voltage limit to check. The default is 0.95.
    max_line_loading : Max line loading limit to check. The default is 100.
    max_trafo_loading : Max trafo loading limit to check. The default is 100.
    p_lim : Max injected power in ext_grid. Default 1000.

    Returns True if all scenarios i feasible, False if at least one scenario fails
    -------------
    critical_lines: list of critical lines
    '''
    line_to_test = contingency_scenario[0]
    trafo_to_test = contingency_scenario[1]
    scenario_counter = 0
    for line_id in line_to_test:
        if net.line.loc[line_id, 'in_service']:
            net.line.loc[line_id, 'in_service'] = False
            check,_ = check_violations(net, run_control = run_control, vmax=vmax, vmin=vmin, max_line_loading=max_line_loading, max_trafo_loading=max_trafo_loading, p_lim=p_lim)
            scenario_counter +=1
            if True in check:
                net.line.loc[line_id, 'in_service'] = True
                return False, scenario_counter
            net.line.loc[line_id, 'in_service'] = True
            #Restore all controlers to inital state
            reset_all_controllers(net)

    for trafo_id in trafo_to_test:
        if net.trafo.loc[trafo_id, 'in_service']:
            net.trafo.loc[trafo_id, 'in_service'] = False
            check,_ = check_violations(net, run_control = run_control, vmax=vmax, vmin=vmin, max_line_loading=max_line_loading, max_trafo_loading=max_trafo_loading, p_lim=p_lim)
            scenario_counter +=1
            if True in check:
                net.trafo.loc[trafo_id, 'in_service'] = True
                return False, scenario_counter
            net.trafo.loc[trafo_id, 'in_service'] = True
            #Restore all controlers to inital state
            reset_all_controllers(net)
    
    return True, scenario_counter
