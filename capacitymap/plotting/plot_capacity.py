"""
Copyright (c) 2016-2021 by University of Kassel and Fraunhofer Institute for Energy Economics
and Energy System Technology (IEE) Kassel and individual contributors (see AUTHORS file for details).
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted 
provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or other materials provided
with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to 
endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR 
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND 
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR 
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, 
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
def pf_res_plotly(net, cmap="Jet", use_line_geodata=None, on_map=False, projection=None,
                  map_style='basic', figsize=1, aspectratio='auto', line_width=2, bus_size=10,
                  climits_volt=(0.9, 1.1), climits_load=(0, 100), cpos_volt=1.0, cpos_load=1.1,
                  filename="temp-plot.html", auto_open=True):
    """
        Plots a pandapower network in plotly
        using colormap for coloring lines according to line loading and buses according to voltage in p.u.
        If no geodata is available, artificial geodata is generated. For advanced plotting see the tutorial
        INPUT:
            **net** - The pandapower format network. If none is provided, mv_oberrhein() will be plotted as an example
        OPTIONAL:
            **respect_switches** (bool, False) - Respect switches when artificial geodata is created
            **cmap** (str, True) - name of the colormap
            **colors_dict** (dict, None) - by default 6 basic colors from default collor palette is used.
                                                Otherwise, user can define a dictionary in the form: voltage_kv : color
            **on_map** (bool, False) - enables using mapbox plot in plotly. If provided geodata are not
                                                    real geo-coordinates in lon/lat form, on_map will be set to False.
            **projection** (String, None) - defines a projection from which network geo-data will be transformed to
                                            lat-long. For each projection a string can be found at http://spatialreference.org/ref/epsg/
            **map_style** (str, 'basic') - enables using mapbox plot in plotly
            - 'streets'
            - 'bright'
            - 'light'
            - 'dark'
            - 'satellite'
            **figsize** (float, 1) - aspectratio is multiplied by it in order to get final image size
            **aspectratio** (tuple, 'auto') - when 'auto' it preserves original aspect ratio of the network geodata
                                                    any custom aspectration can be given as a tuple, e.g. (1.2, 1)
            **line_width** (float, 1.0) - width of lines
            **bus_size** (float, 10.0) -  size of buses to plot.
            **climits_volt** (tuple, (0.9, 1.0)) - limits of the colorbar for voltage
            **climits_load** (tuple, (0, 100)) - limits of the colorbar for line_loading
            **cpos_volt** (float, 1.0) - position of the bus voltage colorbar
            **cpos_load** (float, 1.1) - position of the loading percent colorbar
            **filename** (str, "temp-plot.html") - filename / path to plot to. Should end on `*.html`
            **auto_open** (bool, True) - automatically open plot in browser
        OUTPUT:
            **figure** (graph_objs._figure.Figure) figure object
    """

    version_check()
    if 'res_bus' not in net or net.get('res_bus').shape[0] == 0:
        logger.warning('There are no Power Flow results. A Newton-Raphson power flow will be executed.')
        runpp(net)

    # create geocoord if none are available
    if 'line_geodata' not in net:
        net.line_geodata = pd.DataFrame(columns=['coords'])
    if 'bus_geodata' not in net:
        net.bus_geodata = pd.DataFrame(columns=["x", "y"])
    if len(net.line_geodata) == 0 and len(net.bus_geodata) == 0:
        logger.warning("No or insufficient geodata available --> Creating artificial coordinates." +
                       " This may take some time")
        create_generic_coordinates(net, respect_switches=True)
        if on_map:
            logger.warning("Map plots not available with artificial coordinates and will be disabled!")
            on_map = False
    for geo_type in ["bus_geodata", "line_geodata"]:
        dupl_geo_idx = pd.Series(net[geo_type].index)[pd.Series(
            net[geo_type].index).duplicated()]
        if len(dupl_geo_idx):
            if len(dupl_geo_idx) > 20:
                logger.warning("In net.%s are %i duplicated " % (geo_type, len(dupl_geo_idx)) +
                               "indices. That can cause troubles for draw_traces()")
            else:
                logger.warning("In net.%s are the following duplicated " % geo_type +
                               "indices. That can cause troubles for draw_traces(): " + str(
                    dupl_geo_idx))

    # check if geodata are real geographycal lat/lon coordinates using geopy
    if on_map and projection is not None:
        geo_data_to_latlong(net, projection=projection)

    # ----- Buses ------
    # initializating bus trace
    # hoverinfo which contains name and pf results
    precision = 3
    hoverinfo = (
            net.bus.name.astype(str) + '<br />' +
            'V_m = ' + net.res_bus.vm_pu.round(precision).astype(str) + ' pu' + '<br />' +
            'V_m = ' + (net.res_bus.vm_pu * net.bus.vn_kv.round(2)).round(precision).astype(str) + ' kV' + '<br />' +
            'V_a = ' + net.res_bus.va_degree.round(precision).astype(str) + ' deg').tolist()
    hoverinfo = pd.Series(index=net.bus.index, data=hoverinfo)
    bus_trace = create_bus_trace(net, net.bus.index, size=bus_size, infofunc=hoverinfo, cmap=cmap,
                                 cbar_title='Bus Voltage [pu]', cmin=climits_volt[0], cmax=climits_volt[1],
                                 cpos=cpos_volt)

    # ----- Lines ------
    # if bus geodata is available, but no line geodata
    # if bus geodata is available, but no line geodata
    cmap_lines = 'jet' if cmap == 'Jet' else cmap
    if use_line_geodata is None:
        use_line_geodata = False if len(net.line_geodata) == 0 else True
    elif use_line_geodata and len(net.line_geodata) == 0:
        logger.warning("No or insufficient line geodata available --> only bus geodata will be used.")
        use_line_geodata = False
    # hoverinfo which contains name and pf results
    hoverinfo = (
            net.line.name.astype(str) + '<br />' +
            'I = ' + net.res_line.loading_percent.round(precision).astype(str) + ' %' + '<br />' +
            'I_from = ' + net.res_line.i_from_ka.round(precision).astype(str) + ' kA' + '<br />' +
            'I_to = ' + net.res_line.i_to_ka.round(precision).astype(str) + ' kA' + '<br />').tolist()
    hoverinfo = pd.Series(index=net.line.index, data=hoverinfo)
    line_traces = create_line_trace(net, use_line_geodata=use_line_geodata, respect_switches=True,
                                    width=line_width * 1.5,
                                    infofunc=hoverinfo,
                                    cmap=cmap_lines,
                                    cmap_vals=net.res_line['loading_percent'].values,
                                    cmin=climits_load[0],
                                    cmax=climits_load[1],
                                    cbar_title='Line Loading [%]',
                                    cpos=cpos_load)

    # ----- Trafos ------
    # hoverinfo which contains name and pf results
    hoverinfo = (
            net.trafo.name.astype(str) + '<br />' +
            'I = ' + net.res_trafo.loading_percent.round(precision).astype(str) + ' %' + '<br />' +
            'I_hv = ' + net.res_trafo.i_hv_ka.round(precision).astype(str) + ' kA' + '<br />' +
            'I_lv = ' + net.res_trafo.i_lv_ka.round(precision).astype(str) + ' kA' + '<br />').tolist()
    hoverinfo = pd.Series(index=net.trafo.index, data=hoverinfo)
    trafo_traces = create_trafo_trace(net, width=line_width * 1.5, infofunc=hoverinfo,
                                      cmap=cmap_lines, cmin=0, cmax=100)

    # ----- Ext grid ------
    # get external grid from create_bus_trace
    marker_type = 'circle' if on_map else 'square'
    ext_grid_trace = create_bus_trace(net, buses=net.ext_grid.bus,
                                      color='grey', size=bus_size * 2, trace_name='external_grid',
                                      patch_type=marker_type)
    # --------Power direction arrows for line and trafo-------------

    edge_x = []
    edge_y = []
    edge_trace = []
    # Controls for how the graph is drawn
    nodeColor = 'Blue'
    nodeSize = 20
    lineWidth = 1
    lineColor = '#000000'
    # Line arrows
    for idx, linerow in test_grid.grid.line.iterrows():

        # Set direction based on pf results
        if test_grid.grid.res_line.p_from_mw.loc[idx] >= 0:
            # print('From-to direction')
            line_start = test_grid.grid.bus_geodata[['x', 'y']].loc[linerow.from_bus].values[:]
            line_end = test_grid.grid.bus_geodata[['x', 'y']].loc[linerow.to_bus].values[:]
        elif test_grid.grid.res_line.p_from_mw.loc[idx] < 0:
            # print('To-From direction')
            line_start = test_grid.grid.bus_geodata[['x', 'y']].loc[linerow.to_bus].values[:]
            line_end = test_grid.grid.bus_geodata[['x', 'y']].loc[linerow.from_bus].values[:]

        # create arrow-edge
        edge_x, edge_y = addEdge(line_start, line_end, edge_x, edge_y,
                                 lengthFrac=1, arrowPos='middle', arrowLength=0.2, arrowAngle=25, dotSize=2)
    # Trafo arrows
    for idx, linerow in test_grid.grid.trafo.iterrows():

        # Set direction based on pf results
        if test_grid.grid.res_trafo.p_hv_mw.loc[idx] >= 0:
            # print('From-to direction')
            trafo_start = test_grid.grid.bus_geodata[['x', 'y']].loc[linerow.lv_bus].values[:]
            trafo_end = test_grid.grid.bus_geodata[['x', 'y']].loc[linerow.hv_bus].values[:]
        elif test_grid.grid.res_trafo.p_hv_mw.loc[idx] < 0:
            # print('To-From direction')
            trafo_start = test_grid.grid.bus_geodata[['x', 'y']].loc[linerow.hv_bus].values[:]
            trafo_end = test_grid.grid.bus_geodata[['x', 'y']].loc[linerow.lv_bus].values[:]
        # create arrow-edge
        edge_x, edge_y = addEdge(trafo_start, trafo_end, edge_x, edge_y,
                                 lengthFrac=1, arrowPos='middle', arrowLength=0.2, arrowAngle=25, dotSize=2)
        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=lineWidth, color=lineColor), hoverinfo='none',
                                mode='lines')

    trace = line_traces + trafo_traces + ext_grid_trace + bus_trace + [edge_trace]
    return draw_traces(trace, showlegend=False)