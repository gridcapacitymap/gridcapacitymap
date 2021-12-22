# -*- coding: utf-8 -*-
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
import numpy as np
from pandapower.control.basic_controller import Controller

try:
    import pplog as logging
except ImportError:
    import logging
logger = logging.getLogger(__name__)


class ShuntController(Controller):
    """
    Shunt Controller with fixed steps for voltage control.
    INPUT:
       **net** (attrdict) - Pandapower struct
       **sid** (int) - ID of the shunt that is controlled
       NEW **bid** (int) - Bus ID of for bus which shunt is controlled after
       OLD **side** (string) - 
       **tol** (float) - Voltage tolerance band at bus in Percent
       **in_service** (bool) - Indicates if the element is currently active
       OLD **trafotype** (string) - Type of the controlled trafo ("2W" or "3W")
       NEW **steps** (array of float) - 
       NEW **init_step** (init) - inital step of controller
       
    OPTIONAL:
        **recycle** (bool, True) - Re-use of internal-data in a time series loop.
    """

    def __init__(self, net, sid, bid, tol, in_service, steps, init_step,  level=0, order=0, recycle=True,
                 **kwargs):
        super().__init__(net, in_service=in_service, level=level, order=order, recycle=recycle,
                         **kwargs)
        self.sid = sid
        self.bid = bid
        self.element_in_service = net['shunt'].at[self.sid, "in_service"]
        self.controlled_bus = bid 

        if self.controlled_bus in net.ext_grid.loc[net.ext_grid.in_service, 'bus'].values:
            logger.warning("Controlled Bus is Slack Bus - deactivating controller")
            self.set_active(net, False)
        elif self.controlled_bus in net.ext_grid.loc[
            ~net.ext_grid.in_service, 'bus'].values:
            logger.warning("Controlled Bus is Slack Bus with slack out of service - "
                           "not deactivating controller")

        self.tap_min = 0 
        self.tap_max = len(steps)-1 
        self.init_step = init_step
        self.tap_pos = init_step # net[self.trafotable].at[self.sid, "tap_pos"]
        if np.isnan(self.tap_pos):
            self.tap_pos = 0 

        if np.isnan(self.tap_min) or \
                np.isnan(self.tap_max):
            logger.error("Shunt-Controller has been initialized with NaN values!")

        self.tol = tol
        


    def timestep(self, net):
        self.tap_pos = net[self.trafotable].at[self.sid, "tap_pos"]
        #net[self.shunt].at[self.sid, "q_mvar"] = self.steps[self.tap_pos]


    def __repr__(self):
        s = '%s of %s %d' % (self.__class__.__name__, 'shunt', self.sid)
        return s

    def __str__(self):
        s = '%s of %s %d' % (self.__class__.__name__, 'shunt', self.sid)
        return s