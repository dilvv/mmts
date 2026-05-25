

### 2. Python libraries using Python Virtual Environment
```
python3 -m venv .venv
source .venv/bin/activate
pip3 install   flask   flask-socketio   requests   sphinx   paramiko   pyvisa   pyvisa-py   pyyaml   flask-wtf   myst-parser   flask-cors   pymeasure   psycopg psycopg2-binary
sudo apt update
sudo apt install python3-psycopg python3-psycopg-c
sudo apt update && sudo apt install firewalld
```

### 3. check README.task3.md
Check instructions in **README.task3.md**

### 4. Open firewall
open firewall port 5001 such you can access server [http://127.0.0.1:5001](http://127.0.0.1:5001)
```
#!/usr/bin/env bash

sudo sh scripts/open_firewall.sh
```

### 5. Put this reopsitory as a system service

```
chmod +x ../app.py
### edit path in `data/MMTS.service` and `data/MMTS.service.variables`
python3 data/MMTS.service.createscript.py

sudo cp data/MMTS.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start MMTS.service ### activate service
#sudo systemctl stop  MMTS.service ### stop service
#journalctl -u MMTS.service  ### check error messages
```



## Directly run without GUI
The GUI execute commands in makefile. So use `make help` checking all related commands.

* `make -f makefile_task2 initialize`
* `make -f makefile_task2 run -j3`
* `make -f makefile_task2 stop`
* `make -f makefile_task2 destroy`


## DAQ steps
### step1 initialize
* Turn on kria power
* load all related kria firmwares
### step2 configure

### step3 run
Each single kria runs command. Note that pullerPort should be modified for assigning kria physically.

* reload kria status and activate daq-client at background
    - `ssh root@$kriaIP 'fw-loader load /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v2/'`
    - `ssh root@$kriaIP 'systemctl restart i2c-server.service && systemctl restart daq-server.service'`
    - `ssh root@$kriaIP 'systemctl status i2c-server.service && systemctl status daq-server.service'`
    - `sleep 0.5`
    - `./daq-client -p 6002 &`
* waiting for 8 seconds
* `python3 pedestal_run.py -i $kriaIP -f $yamlfile -d $moduleID -I --pullerPort=6002`



# Debug Region
## 0. Check logging in system
Use `journalctl -u MMTS.service` to check messages.

## 1. Run GUI without creating service
At repository directory, activate python virtual environment and BASH variables using ` source .venv/bin/activate; source ./init_bash_vars.sh `
Then run command `python3 app.py` to activate flask server.

Then open link [https://127.0.0.1:5005](https://127.0.0.1:5005) from browser.

## 2. Direct run command in CLI without flask server
The buttons on flask server executes commands in GNU make.
So you can execute commands
```
#!/usr/bin/env bash

### by default, it shows help information
make -f makefile_task3

# Usage: make <command>
# 		[moduleID1L][moduleID1C][moduleID1R]
# 		[moduleID2L][moduleID2C][moduleID2R]
# 
# Commands:
# 
#   all_IVscan       IV scan does not support multithread
#   initialize       initialize
#   run              all IV scan (only single threaded allowed) [currentTEMPERATURE=20][currentHUMIDITY=50][switch_delay=0]
#   stop             stop pedestal run
#   destroy          remove all running jobs and disable board power
#   help             Display this help
```



```
#!/usr/bin/env bash

### help information
make -f makefile_task3 help

### initialize button
make -f makefile_task3 initialize

### configure button: flask server collects the run argument. So makefile didn't provide this command

### run button. If moduleID not set, skip this Vitrek channel.
make -f makefile_task3 run currentTEMPERATURE=20 currentHUMIDITY=50 switch_delay=0 \
    moduleID1L=320MHF2WDNT0460 moduleID1C=320MHF2WDNT0460 moduleID1R=320MHF2WDNT0460 \
    moduleID2L=320MHF2WDNT0460 moduleID2C=320MHF2WDNT0460 moduleID2R=320MHF2WDNT0460


### stop button.
make -f makefile_task3 stop

### destroy button
make -f makefile_task3 destroy
```

