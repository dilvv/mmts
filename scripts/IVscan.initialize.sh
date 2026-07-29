python3 turn_on_HV_switch.py --position=0 --delay=0 --config=../data/mmts_configurations.yaml

cd ../external_packages/HGCal_Module_Production_Toolkit/
echo python3 scripts/getIV.py --initialize
python3 scripts/getIV.py -i
