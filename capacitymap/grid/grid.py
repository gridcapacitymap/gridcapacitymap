# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to Grid Capacity Map

from datetime import timedelta
from collections import defaultdict
from itertools import chain
from operator import methodcaller
from capacitymap.plotting import ppplotlytweaked as ppptw
import plotly.graph_objs as go
import pandapower as pp
from pandapower.plotting.generic_geodata import create_generic_coordinates
import pandas as pd
import numpy as np
import math
from typing import List
from itertools import chain
try:
    import pplog as logging
except ImportError:
    import logging
logger = logging.getLogger(__name__)


def daterange(start_date, end_date):
    '''
    Parameters
    ----------
    start_date: datetime.date, start date
    end_date: datetime.date, end of timeframe

    Returns generator, from start to end date, including start and end
    '''
    for n in range(-1, int((end_date - start_date).days)):
        yield start_date + timedelta(n+1)


def addEdge(start, end, edge_x, edge_y, lengthFrac=1, arrowPos=None,
            arrowLength=0.025, arrowAngle=30, dotSize=20):
    """
    Parameters
    ---------
    start, end: lists defining start and end points
    edge_x, edge_y: lists used to construct the graph
    arrowAngle: int, angle etween lines in arrowhead in degrees
    arrowLength: float, lenght of lines in arrowhead
    arrowPos: None, 'middle' or 'end', deines where the arrowhead
             should be postioned
    dotSize is the plotly scatter dot size you are using
        (used to even out line spacing when you have a mix of edge lengths)

    Adds edge of arrow to list of edges
    """

    # Get start and end cartesian coordinates
    x0, y0 = start
    x1, y1 = end

    # Incorporate the fraction of this segment covered
    # by a dot into total reduction
    length = math.sqrt((x1-x0)**2 + (y1-y0)**2)
    dotSizeConversion = .0565/20  # length units per dot size
    convertedDotDiameter = dotSize * dotSizeConversion
    lengthFracReduction = convertedDotDiameter / length
    lengthFrac = lengthFrac - lengthFracReduction

    # If the line segment should not cover the entire distance,
    # get actual start and end coords
    skipX = (x1-x0)*(1-lengthFrac)
    skipY = (y1-y0)*(1-lengthFrac)
    x0 = x0 + skipX/2
    x1 = x1 - skipX/2
    y0 = y0 + skipY/2
    y1 = y1 - skipY/2

    # Append line corresponding to the edge
    edge_x.append(x0)
    edge_x.append(x1)
    # Prevents a line being drawn from end of this edge to start of next edge
    edge_x.append(None)
    edge_y.append(y0)
    edge_y.append(y1)
    edge_y.append(None)

    # Draw arrow
    if arrowPos is not None:

        # Find the point of the arrow; assume is at end unless told middle
        pointx = x1
        pointy = y1

        eta = math.degrees(math.atan((x1-x0) / (y1-y0))) if y1 != y0 else 90.0

        if arrowPos == 'middle' or arrowPos == 'mid':
            pointx = x0 + (x1-x0)/2
            pointy = y0 + (y1-y0)/2

        # Find the directions the arrows are pointing
        signx = (x1-x0)/abs(x1-x0) if x1 != x0 else +1    # verify this once
        signy = (y1-y0)/abs(y1-y0) if y1 != y0 else +1    # verified

        # Append first arrowhead
        dx = arrowLength * math.sin(math.radians(eta + arrowAngle))
        dy = arrowLength * math.cos(math.radians(eta + arrowAngle))
        edge_x.append(pointx)
        edge_x.append(pointx - signx**2 * signy * dx)
        edge_x.append(None)
        edge_y.append(pointy)
        edge_y.append(pointy - signx**2 * signy * dy)
        edge_y.append(None)

        # And second arrowhead
        dx = arrowLength * math.sin(math.radians(eta - arrowAngle))
        dy = arrowLength * math.cos(math.radians(eta - arrowAngle))
        edge_x.append(pointx)
        edge_x.append(pointx - signx**2 * signy * dx)
        edge_x.append(None)
        edge_y.append(pointy)
        edge_y.append(pointy - signx**2 * signy * dy)
        edge_y.append(None)

    return edge_x, edge_y

#####################################################################


class Grid:  # 'Common base class for all grids'

    def __init__(self, name, normal_config, config_dict, projects):
        self.name = name
        self.grid = normal_config  # Pandapower net

        # Dictornary over changes in grid. Keys as datetime,
        # every config consists of Object_type, ObjectID and Status
        self.config_dict = config_dict

        # Pandas df, columns Start, End, Object_type, ObjectID, Status
        self.project_df = projects

        self.active_config = None  # list over active configurations
        self.active_date = None  # timestamp for grid, empty=normal operations

        # List of config to go from changed grid to normal operation
        self.normal_operation_config = self.generate_normal_operation_config()

    def generate_normal_operation_config(self):
        normal_operation_config = {'bus': dict(self.grid.bus['in_service']),
                                   'line': dict(self.grid.line['in_service']),
                                   'trafo': dict(self.grid.trafo['in_service']),
                                   'switch': dict(self.grid.switch['closed'])}

        return normal_operation_config

    def display_info(self):
        """
        Prints summarized info over grid
        """
        print("Display grid info")
        print(self.grid)
        # print('Config dict ', dict(list(self.config_dict.items())[0:2]))
        print('Active date ', self.active_date)
        print('Active config ', self.active_config)

    def store_project_and_update_config(self, new_proj):
        """
        Store/Add new project in pandas df over planned projects and store config in dictioanry over config
        :param new_proj: dict with keys: Start, End, Object_type, ObjectID, Status
        Update project df and config_dict
        """
        self.project_df = self.project_df.append(new_proj, ignore_index=True)
        self.config_dict = combine_dict((self.config_dict), generate_config_from_project(new_proj))  # kommentera

    def remove_project_and_update_config(self, proj_to_remove):
        '''
        remove new project from project_df and config_dict - remove entire key from config_dict if it is then empty
        project needs to exist. Assumes there are no duplicated projects

        '''
        clear_config = False #clear config only if project is found
        for idx, row in self.project_df.iterrows():
            
            if dict(row) == proj_to_remove:
                self.project_df = self.project_df.drop(idx)
                clear_config = True
                break

        #if project has been found    
        if clear_config:
            start_time = proj_to_remove['Start']
            end_time = proj_to_remove['End']
            check_dict = dict((k, proj_to_remove[k]) for k in ('Object_type', 'ObjectID', 'Status'))

            for day in daterange(start_time, end_time):
                if day in self.config_dict.keys():
                    if check_dict in self.config_dict[day]:
                        self.config_dict[day].remove(check_dict)
                        if len(self.config_dict[day]) == 0:
                            del self.config_dict[day]


    def config(self):
        """
        Config grid according to selected list of config and save steps to restore normal grid. Update grid and restore
        """
        if self.active_config:
            for config in self.active_config:
                if config['Object_type'] == 'line':
                    idx = self.grid.line[self.grid.line.name == config['ObjectID']].index#.values[0]
                    self.grid.line.in_service.loc[idx] = config['Status']

                elif config['Object_type'] == 'trafo':
                    idx = self.grid.trafo[self.grid.trafo.name == config['ObjectID']].index#.values[0]
                    self.grid.trafo.in_service.loc[idx] = config['Status']

                elif config['Object_type'] == 'switch':
                    idx = self.grid.switch[self.grid.switch.name == config['ObjectID']].index#.values[0]
                    self.grid.switch.closed.loc[idx] = config['Status']
                elif config['Object_type'] == 'bus':
                    idx = self.grid.bus[self.grid.bus.name == config['ObjectID']].index#.values[0]
                    self.grid.bus.in_service.loc[idx] = config['Status']
                else:
                    print('No vaild config')
        # Save steps to change back to normal grid

    def restore(self):
        """
        Restore grid back to normal operation
        Updates, active_config, and active_date
        """
        self.grid.bus['in_service'] = pd.Series(self.normal_operation_config['bus'])
        self.grid.line['in_service'] = pd.Series(self.normal_operation_config['line'])
        self.grid.trafo['in_service'] = pd.Series(self.normal_operation_config['trafo'])
        self.grid.switch['closed'] = pd.Series(self.normal_operation_config['switch'])

        self.active_config = None
        self.active_date = None

    def plot_traces(self, plot_capacity=False, cap_res=None):
        '''
        :return: a go.Figure of traces for the current configuration of the Grid.grid
        '''

        # create geocoord if none are available
        if len(self.grid.line_geodata) == 0 and len(self.grid.bus_geodata) == 0:
            logger.warning("No or insufficient geodata available --> Creating artificial coordinates." +
                        " This may take some time")
            create_generic_coordinates(self.grid)
        colors = ['red', 'black']

        pp.runpp(self.grid)  # do pf when plot to guarantee right flow direction in plot

        # Generate traces
        traceRecode = []

        # trace for power flow direction
        edge_x = []
        edge_y = []

        lineWidth = 1
        lineColor = '#000000'  # arrpow color

        # Line pf directions
        for idx, linerow in self.grid.line.iterrows():
            # Set direction based on pf results
            if self.grid.res_line.p_from_mw.loc[idx] > 0:
                line_start = self.grid.bus_geodata[['x', 'y']].loc[linerow.from_bus].values[:]
                line_end = self.grid.bus_geodata[['x', 'y']].loc[linerow.to_bus].values[:]
            elif self.grid.res_line.p_from_mw.loc[idx] < 0:
                line_start = self.grid.bus_geodata[['x', 'y']].loc[linerow.to_bus].values[:]
                line_end = self.grid.bus_geodata[['x', 'y']].loc[linerow.from_bus].values[:]

            # create arrow-edge
            edge_x, edge_y = addEdge(line_start, line_end, edge_x, edge_y,
                                     lengthFrac=1, arrowPos='middle', arrowLength=0.2, arrowAngle=25, dotSize=2)
        # Trafo pf directions
        for idx, linerow in self.grid.trafo.iterrows():
            # Set direction based on pf results
            if self.grid.res_trafo.p_hv_mw.loc[idx] < 0:
                trafo_start = self.grid.bus_geodata[['x', 'y']].loc[linerow.lv_bus].values[:]
                trafo_end = self.grid.bus_geodata[['x', 'y']].loc[linerow.hv_bus].values[:]
            elif self.grid.res_trafo.p_hv_mw.loc[idx] > 0:
                trafo_start = self.grid.bus_geodata[['x', 'y']].loc[linerow.hv_bus].values[:]
                trafo_end = self.grid.bus_geodata[['x', 'y']].loc[linerow.lv_bus].values[:]
            # create arrow-edge
            edge_x, edge_y = addEdge(trafo_start, trafo_end, edge_x, edge_y,
                                     lengthFrac=1, arrowPos='middle', arrowLength=0.2, arrowAngle=25, dotSize=2)
            
        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=lineWidth, color=lineColor), hoverinfo='none',
                                mode='lines')
        traceRecode.append(edge_trace)

        # hover info for bus, line and trafo
        precision = 3
        hoverinfo_bus = ('Bus: ' +
                         self.grid.bus.name.astype(str) + '<br />' +
                         'V_m = ' + self.grid.res_bus.vm_pu.round(precision).astype(str) + ' pu' + '<br />' +
                         'V_m = ' + (self.grid.res_bus.vm_pu *
                                     self.grid.bus.vn_kv.round(2)).round(precision).astype(str) + ' kV' + '<br />' +
                         'V_a = ' + self.grid.res_bus.va_degree.round(precision).astype(str) + ' deg').tolist()

        hoverinfo_bus = pd.Series(index=self.grid.bus.index, data=hoverinfo_bus)

        hoverinfo_line = ('Line: ' +
                          self.grid.line.name.astype(str) + '<br />' +
                          'Loading = ' + self.grid.res_line.loading_percent.round(precision).astype(str) +
                          ' %' + '<br />' +
                          'I = ' + self.grid.res_line.i_from_ka.round(precision).astype(str) + ' kA' + '<br />'
                          ).tolist()
        hoverinfo_line = pd.Series(index=self.grid.line.index, data=hoverinfo_line)

        hoverinfo_trafo = ('Trafo: ' +
                           self.grid.trafo.name.astype(str) + '<br />' +
                           'Loading = ' + self.grid.res_trafo.loading_percent.round(precision).astype(str) +
                           ' %' + '<br />' +
                           'I_hv = ' + self.grid.res_trafo.i_hv_ka.round(precision).astype(str) + ' kA' + '<br />' +
                           'I_lv = ' + self.grid.res_trafo.i_lv_ka.round(precision).astype(str) + ' kA' + '<br />'
                           ).tolist()
        hoverinfo_trafo = pd.Series(index=self.grid.trafo.index, data=hoverinfo_trafo)

        # append all traces
        traceRecode.append(go.Scatter(pp.plotting.plotly.create_bus_trace(self.grid, infofunc=hoverinfo_bus)[0]))

        for line in ppptw.create_line_trace(self.grid, infofunc=hoverinfo_line, respect_switches=True):
            traceRecode.append(line)

        for trafo in ppptw.create_trafo_trace(self.grid, width=2, infofunc=hoverinfo_trafo, color='green'):
            traceRecode.append(trafo)

        # trace for capacity headroom per bus
        if plot_capacity:
            head = [str(h) for h in cap_res.Headroom.astype('int')]

            headroom_trace = go.Scatter(x=self.grid.bus_geodata.x + 0.2, y=self.grid.bus_geodata.y + 0.2,
                                        mode='text', text=head)
            traceRecode.append(headroom_trace)

        figure = {
            "data": traceRecode,
            "layout": go.Layout(title='Interactive Visualization', showlegend=False, hovermode='closest',
                                margin={'b': 40, 'l': 40, 'r': 40, 't': 40},
                                xaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
                                yaxis={'showgrid': False, 'zeroline': False, 'showticklabels': False},
                                height=600,
                                clickmode='event+select',
                                annotations=[]
                                )}

        return figure
#########################################################################################################################


def generate_config_from_project(new_proj):
    """
    Update project_dict to include new (not yet stored) project
    :param new_proj: New project, dict with keys Start, End, Object_type, ObjectID, Status
    :param proj_dict: dict over projects config
    :return: proj_dict
    """
    config_from_project = {}
    start_date = new_proj['Start']
    end_date = new_proj['End']
    config = {x: new_proj[x] for x in ['Object_type', 'ObjectID', 'Status'] if x in new_proj}
    for day in daterange(start_date, end_date):
        config_from_project[day] = config
    return config_from_project

########################################################################################################################


def combine_dict(d1, d2):
    combined_dict = {}
    for k in set(d1.keys()) | set(d2.keys()):
        combined_dict[k] = []
        for d in (d1, d2):
            if k in d:
                if type(d[k]) is list:
                    for item in d[k]:
                        combined_dict[k].append(item)
                else:
                    combined_dict[k].append(d[k])
    return combined_dict
