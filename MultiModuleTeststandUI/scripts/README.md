This folder stores all bash scripts used on DAQ.
Any scripts should be directly executed in terminal.


Although the `app.py` is able to directly execute these scripts directly,
I'll recommend developer packs the used script into makefile and execute
make commands. As staged commands used for `app.py`, this prevents webpage
handling too much detail.

The designed staged commands:

* `make initialize SomeArgs=myarg`
* `make run -jN SomeArgs=myarg`
  - option `[-jN]` is to run subcommands simultaneous using N threads
* **Configure** command is handled in `app.py`, to providing parameters for `make run`
* `make stop SomeArg=myarg`
  - Since `app.py` kills the threads from `make run`, this command handles some commands after job killed.
* `make destroy SomeArgs=myarg`
  - Since `app.py` kills the threads from `make initialize`, `make run`, `make stop`, this command handles some commands after job killed. For example, disable the board power on kria.

## task2_pedestalrun/

Pedestal run on N kria teststand, these commands do:
1. turn on board power via kria
2. reloaa kria command
3. activate pedestal run according input parameters
4. turn off kria command

* `make -f makefile_task2 initialize JobName=Init`
  - run above commands on each kria teststand
    - `kconn_pwr on`
    - `firewall-cmd --add-port=5555/tcp --add-port=6000/tcp --add-port=8888/tcp --add-port=8080/tcp`
    - `fw-loader load /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v2/`
    - `systemctl restart i2c-server.service && systemctl restart daq-server.service`

* `make -f makefile_task2 run -j2 JobName=Run moduleID1L=320XHT4CPM00019 moduleID1C=320XHF4CPM00160`
  - Use option **moduleID1L** **moduleID1C** **moduleID1R** **moduleID2L** **moduleID2C** **moduleID2R** to trigger the related module. The subcommands would not be executed once the related option remained empty.
  - reload kria system preventing kria failed
    - `fw-loader load /opt/cms-hgcal-firmware/hgc-test-systems/hexaboard-hd-tester-v2p0-trophy-v2/
    - `systemctl restart i2c-server.service && systemctl restart daq-server.service`
  - run commands at current PC. Building connection to kria teststand, analyze type of input module and load related firmware
    - `daq-client -p 6001` running at background
    - `python3 decode_serialnumber_to_module_type.py 320XHF4CPM00160`
    - `python3 pedestal_run.py -i $kriaIP -f $yamlfile -d $moduleID -I --pullerPort=$usedPORT && echo FINISHED`
* `make -f makefile_task2 stop`
  - nothing to do
* `make -f makefile_task2 destroy`
  - disable board power via kria
    - `kconn_pwr off`
