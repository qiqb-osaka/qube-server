#!/bin/bash

# adi_api_mod & qubelsi
cd /root/lib/adi_api_mod && make
cd /root/lib/
pip install ./adi_api_mod/python/qubelsi
# e7awg_sw / quel_clock_master / quel_ic_config
pip install ./e7awg_sw
pip install ./quelware/quel_clock_master
pip install ./quelware/quel_ic_config

# register qube
python $HOME/config/register.py
