#!/bin/bash

# download qube-calib (QubeServer.py included)
#git clone https://github.com/qiqb-osaka/qube-calib.git

# git clone https://github.com/qiqb-osaka/qube-calib-env.git
# cd qube-calib-env
# git submodule update --init
# cd ..

# download quelware
git clone https://github.com/quel-inc/quelware.git
cd quelware/quel_ic_config
./download_prebuilt.sh
tar xfv quelware_prebuilt.tgz  
cd ../..

git clone -b cloud/qiqb-dev https://${GITHUB_TOKEN}@github.com/qipe-nlab/measurement_tool_orion.git
git clone -b cloud/qiqb-dev https://${GITHUB_TOKEN}@github.com/qipe-nlab/measurement_tool_orion_automation.git
git clone https://github.com/tama-sh/sqe_fitting

# download labrad-servers
git clone https://github.com/FeldmanLab/labrad-servers.git
