#!/bin/bash

cd /root/lib/
cd quelware/quel_ic_config
pip install -r requirements_simplemulti_standard.txt -r requirements_dev_addon.txt
cd ../..

# register qube
#python $HOME/config/register.py
