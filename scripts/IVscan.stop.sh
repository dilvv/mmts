cd ../external_packages/HGCal_Module_Production_Toolkit/
python3 scripts/getIV.py --module=0 2>&1 || echo FFFFF && echo ignore the error since the error is expected raising
cd -
python3 turn_on_HV_switch.py --position=0 --delay=0 --config=../data/mmts_configurations.yaml 2>&1 || echo 000 && echo ignore the error 




### error codes
# 1: getIV.py reset failed
# 2: turn_on_HV_switch.py reset failed
