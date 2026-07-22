#!/usr/bin/env python3
import logging
import sys
import os
import ast
from pprint import pformat
import yaml


def load_Andrew_writeconfig(package_path):
    # Convert to absolute path (handles relative paths)
    package_path = os.path.abspath(package_path)
    orig_config_file = os.path.join(package_path, "configuration.yaml")
   #if os.path.exists(orig_config_file):
   #    log.info(f'[UseOriginalConf] configuration.yaml detected in system. Load this configuration file instead of create a new one.')
   #    with open(orig_config_file, 'r') as origconfile:
   #        conf = yaml.safe_load(origconfile)
   #        return conf


    # Target file
    target_file = os.path.join(package_path, "writeconfig.py")

    if not os.path.exists(target_file):
        raise FileNotFoundError(f"writeconfig.py not found in: {package_path}")

    # Parse config_dict without executing module top-level code
    with open(target_file, 'r') as source_file:
        parsed = ast.parse(source_file.read(), filename=target_file)

    config_dict = None
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'config_dict':
                    config_dict = ast.literal_eval(node.value)
                    break
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == 'config_dict':
                config_dict = ast.literal_eval(node.value)

        if config_dict is not None:
            break

    if config_dict is None:
        raise AttributeError("No variable named 'config_dict' found in writeconfig.py")

    log.info(f'[CreateNewConfig] Load conf_dict inside writeconfig.py')
    return config_dict



def mmts_configs(pathto_HGCal_Module_Production_Toolkit, pathto_hgcal_module_testing_gui, urlto_GRAFANAdashbaord):


    mmts_config_dict = {
            'inspector': 'any string',
            'thermalcycle_iterations': {
                'iteration_1': 'iteration_1: room condition, high humidity',
                'iteration_2': 'iteration_2: first low temperature',
                'iteration_3': 'iteration_3: last low temperature',
                'iteration_4': 'iteration_4: final IV, normal temperature',
            },
            'path_HGCal_Module_Production_Toolkit': pathto_HGCal_Module_Production_Toolkit,
            'path_hgcal_module_testing_gui': pathto_hgcal_module_testing_gui,
            'grafana_dashboard_url': urlto_GRAFANAdashbaord,
            'MMTS_hardwares': {
                'keithley': { 'Resource': '', 'Terminal': 'Front', 'WiresPolarization': 'Forward', 'DiscoveryMode': 'by-id' },
                'vitek': { 'Resource': '', 'DiscoveryMode': 'by-id' },
                },
            'MMTS_channel_config': {
                '1L': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6002, 'HVchannel': 1 },
                '1C': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6003, 'HVchannel': 2 },
                '1R': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6004, 'HVchannel': 3 },

                '2L': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6005, 'HVchannel': 4 },
                '2C': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6006, 'HVchannel': 5 },
                '2R': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6007, 'HVchannel': 6 },

                '3L': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6008, 'HVchannel': 7 },
                '3C': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6009, 'HVchannel': 8 },
                '3R': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6010, 'HVchannel': 9 },

                '4L': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6011, 'HVchannel':10 },
                '4C': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6012, 'HVchannel':11 },
                '4R': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6013, 'HVchannel':12 },

                '5L': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6014, 'HVchannel':13 },
                '5C': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6015, 'HVchannel':14 },
                '5R': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6016, 'HVchannel':15 },

                '6L': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6017, 'HVchannel':16 },
                '6C': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6018, 'HVchannel':17 },
                '6R': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6019, 'HVchannel':18 },

                '7L': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6020, 'HVchannel':19 },
                '7C': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6021, 'HVchannel':20 },
                '7R': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6022, 'HVchannel':21 },

                '8L': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6023, 'HVchannel':22 },
                '8C': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6024, 'HVchannel':23 },
                '8R': { 'IP': '', 'type': 'Kria', 'pullerPORT': 6025, 'HVchannel':24 },
            }
    }
    return mmts_config_dict



log = logging.getLogger(__name__)
if __name__ == '__main__':
    loglevel = os.environ.get('LOG_LEVEL', 'INFO') # DEBUG, INFO, WARNING
    DEBUG_MODE = True if loglevel == 'DEBUG' else False
    logLEVEL = getattr(logging, loglevel)
    logging.basicConfig(stream=sys.stdout,level=logLEVEL,
                        format=f'%(levelname)-7s%(filename)s#%(lineno)s %(funcName)s() >>> %(message)s',
                        datefmt='%H:%M:%S')


    ### defualt values
    pathtohgcal_module_testing_gui = 'external_packages/hgcal-module-testing-gui'
    pathtoHGCal_Module_Production_Toolkit = 'external_packages/HGCal_Module_Production_Toolkit'
    urltoGRAFANAdashbaord = ''

    confBASE = load_Andrew_writeconfig(pathtohgcal_module_testing_gui)
    confMMTS = mmts_configs(pathtoHGCal_Module_Production_Toolkit, pathtohgcal_module_testing_gui, urltoGRAFANAdashbaord)

    oFILE = 'data/mmts_configurations.yaml'
    with open(oFILE, 'w') as fout:
        yaml.dump(confBASE, fout)
        yaml.dump(confMMTS, fout)
    log.info(f'[Conf Created] {oFILE} created. You need to fill new values')
