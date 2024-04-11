#!/bin/bash

cd quelware/quel_ic_config
pip install -r requirements_simplemulti_standard.txt
cd ../..

# register qube
python $HOME/config/register.py
