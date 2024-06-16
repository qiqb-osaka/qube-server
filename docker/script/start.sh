#!/bin/bash

export LIB_PATH=/root/lib
export PYTHONPATH=$PYTHONPATH:$LIB_PATH
export PYTHONPATH=$PYTHONPATH:$LIB_PATH/quelware/qube_master
export PYTHONPATH=$PYTHONPATH:$LIB_PATH/measurement_tool_orion:$LIB_PATH/measurement_tool_orion_automation
export QUBECALIB_PATH_TO_ROOT=$LIB_PATH/qube-calib

# make log directory if it doesn't exist
mkdir -p $HOME/log

# start labrad as a background process
labrad &

# env LABRADHOST=localhost \
#       LABRADPASSWORD=Cooper2e \
#       labrad &

# save labrad process id
labrad_pid=$!

# wait until labrad is up and running or timeout
timeout=30  # maximum number of seconds to wait
count=0
# wait until setup.sh script succeeds
while ! /root/script/setup.sh >& /dev/null; do
  sleep 1
  count=$(($count + 1))
  if [ $count -ge $timeout ]; then
    echo "Error: labrad did not start within $timeout seconds."
    exit 1
  fi
done

# start data vault server
python $LIB_PATH/labrad-servers/data_vault.py >& $HOME/log/data-vault.log &

# start qube server
# NOTE: without QUBE_SERVER env, qube server will run in debug mode
QUBE_SERVER="QuBE Server" \
UDP_RW_BIND_ADDRESS="10.0.0.3" \
python $LIB_PATH/qubesrv/app.py >& $HOME/log/qube-server.log &
#python $LIB_PATH/qube-calib/QubeServer.py >& $HOME/log/qube-server.log &

# use 'wait' command to make the script pause and keep the container running
wait $labrad_pid

#tail -f
