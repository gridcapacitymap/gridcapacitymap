# SPDX-License-Identifier: Apache-2.0
# Copyright Contributors to Grid Capacity Map

def reset_all_controllers(net):
    for idx, ctr in net.controller.iterrows():
        ctr.object.restore_init_state(net)