#!/usr/bin/env python3
import logging
import sys
from optparse import OptionParser
from JobModule.device_VITREK_switch_control import Vitrek964i
import asyncio
log = logging.getLogger(__name__)

async def only_turn_on_channel(vitrekINST, iCHANNEL:int):
    if iCHANNEL < 1 or iCHANNEL > 32: raise IOError(f'[InvalidChannel] channel {iCHANNEL} is invalid')
   #await vitrekINST.set_bank_state(0, "#h00") ## reset all relay at bank0
   #await vitrekINST.set_bank_state(1, "#h00") ## reset all relay at bank1
   #await vitrekINST.set_bank_state(2, "#h00") ## reset all relay at bank2
    await vitrekINST.reset() ## reset all relay
    await vitrekINST.set_relay_state(iCHANNEL, "ON")

mmtsPOSmap__ = {
        '0': 0, # resetallchannel
        '1L': 1, '1C': 2, '1R': 3,
        '2L': 4, '2C': 5, '2R': 6,
        '3L': 7, '3C': 8, '3R': 9,
        '4L':10, '4C': 5, '4R': 6,
        '5L': 4, '5C': 5, '5R': 6,
        '6L': 4, '6C': 5, '6R': 6,
        '7L': 4, '7C': 5, '7R': 6,
        '8L': 4, '8C': 5, '8R': 6,
        }
def GetHVChannel(mmtsPOSITION:str, mmtsPOSmap:dict):
    HV_channel = mmtsPOSmap.get(mmtsPOSITION, 0)
    if HV_channel == 0:
        log.info(f'[Reset HVSwitch] mmtsPOSITION "{mmtsPOSITION}" not in mmtsPOSmap, by default it is used to reset HV switch')
    else:
        log.info(f'[TurnOn HVSwitch ch{HV_channel}] mmtsPOSITION "{mmtsPOSITION}" found, turn on ch{HV_channel}')
    return HV_channel
    
#def Option_Parser(argv):
#
#    usage='usage: %prog [options] arg\n'
#    parser = OptionParser(usage=usage)
#
#    parser.add_option('-p', '--position',
#            type='str', dest='position', default=None,
#            help=f'MMTS position. available options is {mmtsPOSmap.keys}. Once option received invalid entry, reset all channel'
#            )
#    parser.add_option('-d', '--delay',
#            type='float', dest='delay', default=0.05,
#            help='delay timer after turn on switch'
#            )
#    parser.add_option('-a', '--address',
#            type='str', dest='address', default=None,
#            help='RS232 device address in system. Input like "ASRL/dev/ttyUSB0::INSTR". If address set, use this address. Or use address in config file'
#            )
#    parser.add_option('-c', '--config',
#            type='str', dest='config', default='data/mmts_configurations.yaml',
#            help='Read RS232 device address like "ASRL/dev/ttyUSB0::INSTR" from yaml file. This option will be ignored if --address set'
#            )
#        
#
#
#    (options, args) = parser.parse_args(argv)
#    return options
def Option_Parser(argv):
    usage = 'usage: %prog [options] arg\n'
    parser = OptionParser(usage=usage)

    pos_choices = sorted(mmtsPOSmap__.keys())

    parser.add_option(
        '-p', '--position',
        type='choice', choices=pos_choices,
        dest='position', default=None,
        help=f"MMTS position. Choices: {', '.join(pos_choices)}, 0 for reset all channel"
    )

    parser.add_option(
        '-d', '--delay',
        type='float', dest='delay', default=0.05,
        help='delay timer after turn on switch'
    )
    parser.add_option(
        '-a', '--address',
        type='str', dest='address', default=None,
        help='RS232 device address in system. Input like "ASRL/dev/ttyUSB0::INSTR". '
             'If address set, use this address. Or use address in config file'
    )
    parser.add_option(
        '-c', '--config',
        type='str', dest='config', default='data/mmts_configurations.yaml',
        help='Read RS232 device address like "ASRL/dev/ttyUSB0::INSTR" from yaml file. '
             'This option will be ignored if --address set'
    )

    (options, args) = parser.parse_args(argv)
    return options




def address_from_yaml(yamlFILE):
    '''
### used for run.IVscan.sh
RS232:
  switch_vitek: 'ASRL/dev/DAQrs232_HVswitch::INSTR'
  HV_keithley: 'ASRL/dev/DAQrs232_keithley::INSTR'
    '''
    import yaml
    with open(yamlFILE, 'r') as fIN:
        conf = yaml.safe_load(fIN)
        return conf['MMTS_hardwares']['vitek']['Resource']

def channel_mapping_from_yaml(yamlFILE):
    '''
    yaml file content as

```
MMTS_channel_config:
  1L:
    IP:
    type: Kria
    pullerPORT: 6002
    HVchannel: 1 ### used for IV scan channel
  1C:
    IP:
    type: Kria
    pullerPORT: 6003
    HVchannel: 2
  1R:
    IP: 
    type: Kria
    pullerPORT: 6004
    HVchannel: 3
  2L:
    IP: 
    type: Trenz
    pullerPORT: 6005
    HVchannel: 4
  2C:
    IP: 
    type: Kria
    pullerPORT: 6006
    HVchannel: 5
  2R:
    IP: 
    type: Kria
    pullerPORT: 6007
    HVchannel: 6
```
    
    And read tag 1L and HVchannel 1.
    '''
    import yaml
    with open(yamlFILE, 'r') as fIN:
        conf = yaml.safe_load(fIN)
        mmts_position_map = {
                mmts_position: int(conf['HVchannel'])
            for mmts_position, conf in conf['MMTS_channel_config'].items()
        }
        return mmts_position_map
    

def main():
    options = Option_Parser(sys.argv[1:])

    """Comprehensive example usage of the Vitrek964i class with all methods"""
    # Create controller instance
    log.debug(f'[options] {options}')


    addr = options.address if options.address else address_from_yaml(options.config)
    mmts_position_map = channel_mapping_from_yaml(options.config)
    vitrek_device = Vitrek964i(addr)
    try:
        async def async_main(vitrek):
            # Connect to the device
            if await vitrek.connect():
                log.debug("\n===== BASIC DEVICE INFORMATION =====")
                # Get device identity
                identity = await vitrek.get_identity()
                log.debug(f"Device identity: {identity}")

                # Reset device
                await vitrek.reset()
                log.debug("Device reset completed")

                # Check if connected
                connected = vitrek.is_connected()
                log.debug(f"Connected status: {connected}")

                channel = GetHVChannel(options.position, mmts_position_map)
                if channel == 0:
                    await vitrek.reset()
                else:
                    log.info(f'[SetCH] channel {channel} ON')
                    await only_turn_on_channel(vitrek, channel)
                    if options.delay > 0:
                        await asyncio.sleep(options.delay)
        asyncio.run(async_main(vitrek_device))

    except Exception as e:
        log.error(f"Error during operation: {e}")
    finally:
        # Always disconnect properly
        #vitrek_device.disconnect()
        #print("Test sequence completed")
        pass ### not to reset device

if __name__ == '__main__':
    import os
    loglevel = os.environ.get('LOG_LEVEL', 'INFO') # DEBUG, INFO, WARNING
    DEBUG_MODE = True if loglevel == 'DEBUG' else False
    logLEVEL = getattr(logging, loglevel)
    logging.basicConfig(stream=sys.stdout,level=logLEVEL,
                        format=f'%(levelname)-7s%(filename)s#%(lineno)s %(funcName)s() >>> %(message)s',
                        datefmt='%H:%M:%S')
    main()


