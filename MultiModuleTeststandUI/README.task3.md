# Task3 as IV scanning

# Installation
Check the RS232 devices and fill address in **data/mmts_configurations.yaml**
```
RS232:
 ### by default, you can use system assigned address.
 #switch_vitek: 'ASRL/dev/ttyUSB0::INSTR'
 #HV_keithley: 'ASRL/dev/ttyUSB1::INSTR'
 ### Or you can create an alias to identify RS232 adapter
  switch_vitek: 'ASRL/dev/rs232_HVswitch::INSTR'
  HV_keithley: 'ASRL/dev/DAQrs232_keithley::INSTR'
 ### Or you can search the id in system
 #switch_vitek: 'ASRL/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_EUDQb11BS12-if00-port0::INSTR'
 #HV_keithley: 'ASRL/dev/serial/by-id/usb-FTDI_USB_Serial_Converter_FT9GC67T-if00-port0::INSTR'
```


# Commands
### make -f makefile_task3 initialize
Check the RS232 devices connected to computer or not.
Read RS232 adapter `data/mmts_configurations.yaml` and try to send command to initialize machine.


### make -f makefile_task3 run
Despite from pedestal run, IV scan cannot be multithreaded. So `-jN` is forbidden.
Also 1+3 plots are generated at output directory **tmp_files/outs/**.
1. module based plot
2. Summary plots for room temperature / -40 and +20 for all historical modules.


### make -f makefile_task3 stop
Reset the state of Keithley and HV switch

### make -f makefile_task3 destroy
Reset the state of Keithley and HV switch


# Channel mapping
There exists 2 indexes **Flask server ID**, **Vitek HV Channel ID**.
**Flask server ID** is the labels used in webpage. It is labeled **moduleID1L**, **moduleID1C**, **moduleID1R**, **moduleID2L**, **moduleID2C**, **moduleID2R**
And these labels should map to chamber position, ideally chamber have 8 layer and have **left**, **center** and **right**. So the labels are **1L**, **1C** and **1R**.


**Vitek HV Channel ID** is the hardware index on rare panel. In case it shows channel 1~24.
The mapping in file **scripts/turn_on_HV_switch.py** is configured here
```
mmtsPOSmap = {
        '0': 0, # If "0" received, Vitek will reset all channel
        '1L': 1, '1C': 2, '1R': 3,
        '2L': 4, '2C': 5, '2R': 6,
        }
```
