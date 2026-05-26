## Installations
Use mini conda handling the python libraries. Note that this GUI should be deployed on Linux.
We recommended you use SSH forward 
To install the dependency, you need to use the following commands:

### 1. Clone This Repository and external package
```
### clone this repository
git clone git@github.com:ltsai323/MultiModuleTestUI.git
if [ "$?" != 0 ] && echo "[ERROR - UnableToCloneMMTS] Failed to clone MMTS"

cd MultiModuleTeststandUI

### initialize this GUI
make -f makefile_initialize_this_GUI help
```

```
make -f makefile_initialize_this_GUI help

# Usage: make <command> [opts]
# 
# Commands:
# 
#   task1a_setup_andrewGUI  clone Andrew's GUI and edit configuration. If you installed andrewGUI, use andrewGUI_install_path to link folder. [andrewGUI_install_path=/some/path/to/hgcal-module-testing-gui]
#   task1b_create_daqclient_service  edit daq-client.service for using port 6002~6025. And put them into ~/.config/systemd/user/. Use `systemctl --user restart daq-client-port6001.service` to active service
#   task1c_create_output_folder  make directory from hgcal-module-testing-gui/configuration.yaml
#   task3a_clone_IVscan_codes  clone IV scan packages
#   task3b_create_mmts_configuration  create mmts_configuration
#   flaska_open_firewall_port5001  open firewall port 5001 such you can access server http://127.0.0.1:5001
#   flaskb_make_virtual_environment  create python virtual envuironment
#   flaskc_make_app_as_system_service  make this MultimoduleTeststandUI as a system service
#   help             Display this help
```

```
### all initialize actions
make -f makefile_initialize_this_GUI task1a_setup_andrewGUI  andrewGUI_install_path=/some/path/to/hgcal-module-testing-gui
make -f makefile_initialize_this_GUI task1b_create_daqclient_service
make -f makefile_initialize_this_GUI task1c_create_output_folder
make -f makefile_initialize_this_GUI task3a_clone_IVscan_codes
make -f makefile_initialize_this_GUI task3b_create_mmts_configuration
### Need to modify **data/mmts_configurations.yaml**, this yaml config file will be used in flask DAQ and `external_packages/HGCal_Module_Production_Toolkit` for Andrew's GUI.
make -f makefile_initialize_this_GUI flaska_open_firewall_port5001
make -f makefile_initialize_this_GUI flaskb_make_virtual_environment
make -f makefile_initialize_this_GUI flaskc_make_app_as_system_service
```

Note: PyMeasure is pinned to `0.14.0` in the virtual environment setup because newer PyMeasure releases changed the Keithley 2400 implementation.






## Run GUI
```
#!/usr/bin/env bash
source .venv/bin/activate
source ./init_bash_vars.sh
.venv/bin/python3 app.py
```
then open the link [http://127.0.0.1:5001](http://127.0.0.1:5001)







