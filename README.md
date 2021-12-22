# Grid Capacity Map 
Grid Capacity map is an open source framework for grid capacity calculation and visualisation written in python. For capacity calcualtion a systematic method utilising standard 
power flow analysis is used. Grid capacity Map is using on Pandapowers grid model and power flow calcualtion, more information about pandapower can be found on `www.pandapower.org

The purpose is to be able to give early indication to customers that want to connect to the grid. The aim is to ensure customer and stakeholders expectations on grid 
connections are realistic to give a better connection experience with fewer surprises for both grid owner (DSO/TSO), grid customers and other stakeholders.

Guided tutorials show how the functions can be applied to business use case:
1.  As a new customer, 
I want to see whether I can connect at a grid connection point
2. As a connection request handler,
I want to be able to quickly give preliminary answers to new connection requests
3. As a customer relation coordinator, 
I want to proactively help my customer finding suitable connection points for their needs
4. As a operation planner,
I want to get an overview of past, current and future grid configurations
5. As a operation planner,
I want to get an initial indicator of whether I can accept new projects.
6. As a operation planner,
I want to see remaining capacity at a specific location for a given operation conditions


# Getting Started
1.	Clone this repository
2.	Make sure alll dependecies in requirements.txt is installed in your environment
3.	Start testing the tutorials and the functions

# Folder structure
```|
gridcapacitymap
├── capacitymap                 # 
|  ├── analysis                 # 
|  |  ├── analysis_check.py         # contains functions for perform pf and check results against thresholds and N-1
|  |  ├── capacity_analysis.py      # binary search for finding available capacity at every node
|  |  └── timeseries.py             # timeseries analysis with timedependent grid model
|  ├── controllers              # controller class for discrete tap transformers and discrete shunt controller
|  ├── converter                # method for reading psse .raw file to pandapower network
|  ├── grid                     # grid class, handeling a timedependent grid model
|  └── plotting                 # contains 
└── tutorials               # Contains notebook and exempel data implementation of functions
```
# Contribute
