#!/usr/bin/env sh
kriaIP=${1:-192.168.50.152}
if [ "$BASH_SCRIPT_FOLDER" == "" ]; then echo "[EnvironmentFailure] Required variable BASH_SCRIPT_FOLDER not set. Load use_python_lib.sh"; exit; fi
source $BASH_SCRIPT_FOLDER/step0.functions.sh

#exec_at_kria_IP $kriaIP 'firewall-cmd --add-port=5555/tcp --add-port=6000/tcp --add-port=8888/tcp --add-port=8080/tcp' || the_exit "[step2] Kria failed to open firewall"
exec_at_kria_IP $kriaIP 'fw-loader load /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v2/' || the_exit "[step2] Kria failed to load firmware for HD hexaboard"
#exec_at_kria 'fw-loader load /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3/ && systemctl restart i2c-server.service && systemctl restart daq-server.service'
exec_at_kria_IP $kriaIP 'systemctl restart i2c-server.service && systemctl restart daq-server.service'
exec_at_kria_IP $kriaIP 'systemctl status i2c-server.service && systemctl status daq-server.service'

<<LISTED_OUTPUT_MESG

" 2.ERROR
Previously loaded firmware: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v2/
Using bitstream: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3/hexaboard-hd-tester-v2p0-trophy-v3.bit
Using device tree overlay: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3//device-tree/pl.dtbo
Loading the bitstream took: 3.405s
Loaded the device tree overlay successfully using the zynqMP FPGA manager
step2.kria_env_setup.sh: line 15:
terminate called after throwing an instance of 'zmq::error_t'
  what():  Address already in use
: command not found
"


" 2.SUCCESS
Previously loaded firmware: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3/
Using bitstream: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3/hexaboard-hd-tester-v2p0-trophy-v3.bit
Using device tree overlay: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3//device-tree/pl.dtbo
Loading the bitstream took: 3.431s
Loaded the device tree overlay successfully using the zynqMP FPGA manager
"

" 2.SUCCESS but run twice
Previously loaded firmware: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3/
Using bitstream: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3/hexaboard-hd-tester-v2p0-trophy-v3.bit
Using device tree overlay: /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v3//device-tree/pl.dtbo
Loading the bitstream took: 3.397s
Loaded the device tree overlay successfully using the zynqMP FPGA manager
"



" 1.SUCCESS, the message should be ignored
success
Warning: ALREADY_ENABLED: '5555:tcp' already in 'public'
Warning: ALREADY_ENABLED: '6000:tcp' already in 'public'
Warning: ALREADY_ENABLED: '8888:tcp' already in 'public'
Warning: ALREADY_ENABLED: '8080:tcp' already in 'public'
"
LISTED_OUTPUT_MESG
