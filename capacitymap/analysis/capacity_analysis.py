# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to Grid Capacity Map

import pandas as pd
from time import sleep
import sys
import pandapower as pp
from capacitymap.analysis import analysis_check

def add_loadgen(net_t, loadorgen, conn_at_bus, size_p, size_q):
    """
    Adds a load or generation to the net.load or net.sgen table.
    Adds profile name to the profiles variable of the newly addded capacity.

    INPUT
        net_t (PP net) - Pandapower net
        loadorgen (str) - 'sgen' or 'load' for generation or load for additional capacity connected
        conn_at_bus (int) - Bus at which additional capacity is connected

    OUTPUT
        net_t (PP net) - Updated Pandapower net
    """

    if loadorgen == "load":
        pp.create_load(net_t, conn_at_bus, p_mw=size_p, q_mvar=size_q, name='Cap test')

    elif loadorgen == "sgen":
        pp.create_sgen(net_t, conn_at_bus, p_mw=size_p, q_mvar=size_q, name='Cap test')

    return net_t


def remove_added_loadgen(net_t, loadorgen):
    """
    Removes load or sgen namned Cap test

    INPUT
        net_t (PP net) - Pandapower net
        loadorgen (str) - 'sgen' or 'load' for generation or load for additional capacity connected

    OUTPUT
        net_t (PP net) - Updated Pandapower net
    """
    if loadorgen == "load":
        net_t.load = net_t.load.drop(net_t.load[net_t.load.name == 'Cap test'].index)

    elif loadorgen == "sgen":
        net_t.sgen = net_t.sgen.drop(net_t.sgen[net_t.sgen.name == 'Cap test'].index)

    return net_t


def feas_chk(net, conn_at_bus, loadorgen, size_p, size_q, normal_limits, contingency_limits,contingency_scenario ):
    """
    Initializes the PPnet,
    Adds additional capacity,
    Run pf
    Checks for violations (internal + external)

    INPUT
        net (PP net) - Pandapower net

        loadorgen (str) - 'sgen' or 'load' for generation or load for additional capacity connected
        conn_at_bus (int) - Bus at which additional capacity is connected
        size_p (int) - Size of active power of additional capacity
        size_q (int) - Size of reactive power of additional capacity

    OUTPUT
        feas_result (bool) - 'True' for feasible, 'False' for not feasible
    """

    net = add_loadgen(net, loadorgen, conn_at_bus, size_p, size_q)
    #check normal operations
    if normal_limits==None:
        violation_results, exp = analysis_check.check_violations(net)
    else:
        violation_results, exp = analysis_check.check_violations(net,vmax=normal_limits['vmax'], 
                                                                vmin=normal_limits['vmin'], 
                                                                max_line_loading=normal_limits['max_line_loading'], 
                                                                max_trafo_loading=normal_limits['max_trafo_loading'], 
                                                                p_lim=normal_limits['subscription_p_limits'],
                                                                run_control=normal_limits['run_controllers'])
    feas_result = not (True in violation_results)

    #if normal op. feasible, check contingency
    if feas_result:

        if contingency_limits is None:
            
            feas_result,no_tests =analysis_check.simple_contingency_test(net, contingency_scenario=contingency_scenario)
        else:
            feas_result,no_tests =analysis_check.simple_contingency_test(net,vmax=contingency_limits['vmax'], 
                                                                vmin=contingency_limits['vmin'], 
                                                                max_line_loading=contingency_limits['max_line_loading'], 
                                                                max_trafo_loading=contingency_limits['max_trafo_loading'], 
                                                                p_lim=contingency_limits['subscription_p_limits'],
                                                                run_control=contingency_limits['run_controllers'],
                                                                contingency_scenario=contingency_scenario)
      


        #print('Test power ' + str(size_p) + ' at bus '+ str(conn_at_bus))
        #print('Results contingency' + str(feas_result) + ' number of tested scenarios ' +  str(no_tests))
    net = remove_added_loadgen(net, loadorgen)

    return feas_result, net, exp


def max_cap(net, conn_at_bus, loadorgen, upper_lim_p, lower_lim_p, q, s_tol, normal_limits, contingency_limits,contingency_scenario ):
    """
    ...
    INPUT

    OUTPUT

    """
    no_iter = 0
    [upper_lim_check, mid_check, lower_lim_chk] = False, False, False
    while (not (((upper_lim_p - lower_lim_p) < s_tol)) | (upper_lim_check & mid_check) | (no_iter > 10)):
        no_iter = no_iter + 1
        mid_p = lower_lim_p + (upper_lim_p - lower_lim_p) / 2
        #On first iteration test if upper limit is available and if true break
        if no_iter==1:
            upper_lim_check, net, exp = feas_chk(net, conn_at_bus, loadorgen, upper_lim_p, q, normal_limits, contingency_limits,contingency_scenario)
            if upper_lim_check:
                print('Max capacity is available')
                return upper_lim_p

        else:
            mid_check, net,exp = feas_chk(net, conn_at_bus, loadorgen, mid_p, q, normal_limits, contingency_limits,contingency_scenario )
            if mid_check:  # If mid point is feasible update lower lim, headroom above mid point
                lower_lim_p = mid_p
                

            elif not mid_check:  # If mid point is NOT feasible, headroom is below -> update upper_lim_p to mid_point

                upper_lim_p = mid_p
            

    return lower_lim_p


def headroom(net, loadorgen, upper_lim_p,normal_limits = None, contingency_limits=None,contingency_scenario=[[],[]]):
    low_lim_p = 0  # min added load (MW)   ll_p
    q = 0
    s_tol = 5  # tolerance in search algorithm
    headroom = pd.DataFrame(columns=["Headroom"])
    
    n=len(net.bus)
    
    analysis_check.check_violations.counter = 0 #to track number of powerflows
    i = 0
    for connect_bus in net.bus.index:
        head = max_cap(net, connect_bus, loadorgen, upper_lim_p, low_lim_p, q, s_tol, normal_limits, contingency_limits,contingency_scenario)

        headroom.loc[connect_bus] = head
        #print progress bar
        j = (i + 1) / n
        sys.stdout.write('\r')
        # the exact output you're looking for:
        sys.stdout.write("[%-20s] %d%% (number of PFs: %d)" % ('='*int(20*j), 100*j, analysis_check.check_violations.counter))
        sys.stdout.flush()
        sleep(0.25)
        i +=1
    return headroom