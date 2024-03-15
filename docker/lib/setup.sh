#!/bin/bash

# download qube-calib (QubeServer.py included)
git clone https://github.com/qiqb-osaka/qube-calib.git

# download adi_api_mod and build
git clone https://github.com/qiqb-osaka/adi_api_mod.git

# download e7awg_sw (use simple_multi branch instead of main)
#git clone -b simple_multi https://github.com/e-trees/e7awg_sw.git
git clone https://github.com/qiqb-osaka/qube-calib-env.git
cd qube-calib-env
git submodule update --init
cd ..

# download qube_master with additional libraries from local directory
git clone https://github.com/quel-inc/qube_master.git

git clone -b feature/add_qube_instrument_freq_fix https://${GITHUB_TOKEN}@github.com/qipe-nlab/measurement_tool_orion.git
git clone -b ysuzuki/dev https://${GITHUB_TOKEN}@github.com/qipe-nlab/measurement_tool_orion_automation.git
git clone https://github.com/tama-sh/sqe_fitting

# download quelware
git clone https://github.com/quel-inc/quelware.git

# download labrad-servers
git clone https://github.com/FeldmanLab/labrad-servers.git
