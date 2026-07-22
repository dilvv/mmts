#!/usr/bin/env sh
if [ "$BASH_SCRIPT_FOLDER" == "" ]; then echo "[EnvironmentFailure] Required variable BASH_SCRIPT_FOLDER not set. Load use_python_lib.sh"; exit; fi
source $BASH_SCRIPT_FOLDER/step0.functions.sh

exec_at_ctrlpc 'pkill daq-client'
exec_at_ctrlpc 'daq-client'
#ssh ctrlpc 'ls'

### errors
<<LISTED_OUTPUT_MESG
" ERR : Means daq-client already exist. It should be killed or ignore?
terminate called after throwing an instance of 'zmq::error_t'
  what():  Address already in use
"


" SUC
INITIALIZE:
hw_type: LD
outputDirectory: data
run_type: default
serverIP: 192.168.50.180
zmqPushPull_port: 8888
CONFIGURE
START
	 save roc data in : /home/ntucms/electronic_test_kria/HD_bottom/data/mytest/pedestal_run/run_20250225_190653//pedestal_run0.raw
END_OF_RUN
STOP
"
### Problems: hw_type: LD <---- is it LD?

" ERROR : if nothing happened for 20 second
"

LISTED_OUTPUT_MESG
