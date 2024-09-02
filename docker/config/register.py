"""
Registers the QuBE server with the labrad registry.
"""
import json
import labrad

# connect to the labrad manager
cxn = labrad.connect()

# create the directory for the qube server
reg = cxn.registry
reg.cd(["Servers", "Data Vault", "Repository"])
reg.set("kappa_docker", "/home/labrad/labrad-data")
