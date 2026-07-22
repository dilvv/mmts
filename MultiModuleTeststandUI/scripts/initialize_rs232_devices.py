#!/usr/bin/env python3
import logging
import sys
import argparse


log = logging.getLogger(__name__)

import time
import pyvisa


def check_device_connected(resource_name):
    """Check if a device is connected to the specified resource."""
    rm = pyvisa.ResourceManager('@py')

    try:
        # Attempt to open a connection to the resource
        instrument = rm.open_resource(resource_name)
        # If successful, close the session immediately
        instrument.close()
        log.debug(f"{resource_name} is connected.")
        return True
    except pyvisa.VisaIOError as e:
        # Handling specific exceptions related to VISA I/O operations
        log.debug(f"Failed to connect to {resource_name}. Error: {e}")
        return False
    except Exception as e:
        log.debug(f"An error occurred: {e}")
        return False

def ArgParses():
    parser = argparse.ArgumentParser(description="Valid RS232 device connected to this computer")
    
    # The `nargs='+'` allows one or more arguments to be captured as a list
    required_opts = parser.add_argument_group('required arguments')
    required_opts.add_argument('yamlENTRY', nargs='+', type=str, help='Entries for RS232 address recorded in the yaml file, you can put lots of entries separated with space. Ex:RS232/switch_vitek  RS232/HV_keithley')
    # Add an optional argument for a custom string
    required_opts.add_argument('-c', '--config', type=str, help='yaml configurration reading RS232 address', required=True)

    args = parser.parse_args()
    
    # args.strings will be a list of input strings
    log.debug(f"Received yaml entry: {args.yamlENTRY}")
    return args


def read_rs232_addrs(args):
    import yaml
    addrs = {}
    with open(args.config, 'r') as fIN:
        c = yaml.safe_load(fIN)
        for dict_str in args.yamlENTRY: ### dict_str as RS232/switch_vitek
            entries = dict_str.split('/')
            cc = c
            for entry in entries[:-1]:
                cc = cc[entry]
            key = entries[-1]
            val = cc[key]
            addrs[key] = val
    return addrs

            



if __name__ == '__main__':
    import os
    loglevel = os.environ.get('LOG_LEVEL', 'INFO') # DEBUG, INFO, WARNING
    DEBUG_MODE = True if loglevel == 'DEBUG' else False
    logLEVEL = getattr(logging, loglevel)
    logging.basicConfig(stream=sys.stdout,level=logLEVEL,
                        format=f'%(levelname)-7s%(filename)s#%(lineno)s %(funcName)s() >>> %(message)s',
                        datefmt='%H:%M:%S')


    args = ArgParses()
    rs232_addr_dict = read_rs232_addrs(args)
    for rs232NAME, rs232ADDR in rs232_addr_dict.items():
        connected = check_device_connected(rs232ADDR)
        if not connected:
            raise IOError(f'[InvalidRS232Device] Device "{rs232NAME}" of address "{rs232ADDR}" is an invalid entry. check config "{args.config}".')
