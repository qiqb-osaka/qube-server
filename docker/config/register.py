"""
Registers the QuBE server with the labrad registry.
"""
import json
import labrad

# connect to the labrad manager
cxn = labrad.connect()

# create the directory for the qube server
reg = cxn.registry
reg.cd("Servers")
reg.mkdir("QuBE")
reg.cd("QuBE")

# set the parameters for the qube server
reg.set("adi_api_path", "/root/lib/adi_api_mod")
reg.set("master_link", "10.3.0.255")

with open("/root/config/possible_links.json", encoding="utf-8") as f:
    possible_links_dict = json.load(f)
    reg.set("possible_links", json.dumps(possible_links_dict))

with open("/root/config/chassis_skew.json", encoding="utf-8") as f:
    possible_links_dict = json.load(f)
    reg.set("chassis_skew", json.dumps(possible_links_dict))
