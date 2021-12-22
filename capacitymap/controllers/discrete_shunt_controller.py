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



from capacitymap.controllers.shunt_controller import ShuntController

class DiscreteShuntControl(ShuntController):
    """
    Shunt Controller with with discrete steps controlling voltage at bus bid.
    INPUT:
        **net** (attrdict) - Pandapower struct
        **sid** (int) - ID of the shunt that is controlled
        **bid** (int) - Bus ID for at which bus the voltage is steering this controller
        **vm_lower_pu** (float) - Lower voltage limit in pu
        **vm_upper_pu** (float) - Upper voltage limit in pu
        **steps** (array of float) - Array of steps, ordered in decending. Ex. [100, 0, -100.0, -250.0]
        **init_step** (int) - Initial step, must be a valid index in steps 
    OPTIONAL:
        **tol** (float, 0.001) - Voltage tolerance band at bus in Percent (default: 1% = 0.01pu)
        **in_service** (bool, True) - Indicates if the controller is currently in_service
        **drop_same_existing_ctrl** (bool, False) - Indicates if already existing controllers of the same type and with the same matching parameters (e.g. at same element) should be dropped
    """

    def __init__(self, net, sid,bid, vm_lower_pu, vm_upper_pu, steps, init_step,
                 tol=1e-3, in_service=True, order=0, drop_same_existing_ctrl=False,
                  **kwargs):
        
        super(DiscreteShuntControl, self).__init__(net, sid, bid, tol, in_service, steps, init_step, order,**kwargs)

        self.vm_lower_pu = vm_lower_pu
        self.vm_upper_pu = vm_upper_pu
        self.steps = steps
        self.tap_pos = init_step
        self.init_step = init_step
        self.tested_steps = [] 
   
    def control_step(self, net):
        """
        Implements one step of the Discrete controller, always stepping only one tap position up or down
        """
        vm_pu = net.res_bus.at[self.controlled_bus, "vm_pu"]
        

        #Check in which direction to controll the shunt. 
        if vm_pu < self.vm_lower_pu: #if voltage is lower then lower lim, move to the right(increase injected reactive power)
            self.tap_pos += 1 
        elif vm_pu > self.vm_upper_pu: #if voltage is above upper lim, move to the left (decrease injected reactive power)
            self.tap_pos -= 1 
        
        
        self.tested_steps.append(self.tap_pos) #add tap_pos to tested steps
        # WRITE TO NET
        net['shunt'].at[self.sid, "q_mvar"] = self.steps[self.tap_pos]

    def is_converged(self, net):
        """
        Checks if the voltage is within the desired voltage band, then returns True
        """
        #check if controller has shunt in net if not do not include controller
        #  or if controller shunt is out of service do not include controller
        
        if not self.sid in net['shunt'].index or \
           not net['shunt'].at[self.sid, 'in_service']:
            return True

        #Quality check that controller step pos and net.shunt value match
        if not self.steps[self.tap_pos]==net['shunt'].at[self.sid, "q_mvar"]:
            if net['shunt'].at[self.sid, "q_mvar"] not in self.steps:
                self.tap_pos=self.init_step
                # WRITE TO NET
                net['shunt'].at[self.sid, "q_mvar"] = self.steps[self.tap_pos]

            else:
                self.tap_pos = self.steps.index(net['shunt'].at[self.sid, "q_mvar"])
        

        vm_pu = net.res_bus.at[self.controlled_bus, "vm_pu"]
        


        # render this controller converged if it cant reach the desired point
        if vm_pu < self.vm_lower_pu and self.tap_pos == self.tap_max: 
            return True
        elif vm_pu > self.vm_upper_pu and self.tap_pos == self.tap_min:
            return True
        elif len(self.tested_steps) != len(set(self.tested_steps)): #if size of step results in going from to low voltage directly to to high or vice versa
            # WRITE TO NET
            net['shunt'].at[self.sid, "q_mvar"] = self.steps[self.tested_steps[-1]] #set q_mvar to the last tested signal and then accept that the criteria is not met.
            return True
        
        return self.vm_lower_pu < vm_pu < self.vm_upper_pu 

    def restore_init_state(self, net):
        self.tap_pos = self.init_step
        net['shunt'].at[self.sid, "q_mvar"] = self.steps[self.tap_pos]
        self.tested_steps = [] 

        