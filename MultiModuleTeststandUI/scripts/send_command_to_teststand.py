#!/usr/bin/env python3

import logging
import sys

log = logging.getLogger(__name__)

def SkipCMD(runCOND, confCONTENT):
    
    log.debug(f'[GotCOND] SkipCMD() got condiction "{runCOND}"')
    if runCOND == 'all': return False
    if runCOND == 'TranzOnly': return confCONTENT['type'] != 'Tranz'
    if runCOND == 'KriaOnly' : return confCONTENT['type'] != 'Kria'
    log.warning(f'[InvalidCOND] SkipCMD() got invalid condiction "{runCOND}". So no any command will be executed')
    
    return True


if __name__ == '__main__':
    import os
    loglevel = os.environ.get('LOG_LEVEL', 'INFO') # DEBUG, INFO, WARNING
    DEBUG_MODE = True if loglevel == 'DEBUG' else False
    logLEVEL = getattr(logging, loglevel)
    logging.basicConfig(stream=sys.stdout,level=logLEVEL,
            format='send_command_to_teststand.py %(levelname)s - %(message)s',
            datefmt='%H:%M:%S')

    mmtsCONF = sys.argv[1]
    runCOND  = sys.argv[2] ### run condiction 'all' 'KriaOnly' 'TransOnly'
    bashCMD  = sys.argv[3]
    
    import yaml
    with open(mmtsCONF,'r') as fIN:
        conf = yaml.safe_load(fIN)
        
        ssh_key = conf.pop('PCKeyLoc')
        for mmtsPOS, confCONTENT in conf['MMTS_channel_config'].items():
            ipADDR = confCONTENT['IP']
            tsKIND = confCONTENT['type']
            if not ipADDR:
                log.info(f'[Skip] position {mmtsPOS} skipped due to no IP address')
                continue
            if SkipCMD(runCOND, confCONTENT):
                log.info(f'[Skip] position {mmtsPOS} skipped due to SkipCMD()')
                continue
            log.info(f'[BashCMD] ssh -i {ssh_key} root@{ipADDR} "{bashCMD}"')
            os.system(f'ssh -i {ssh_key} root@{ipADDR} "{bashCMD}"')
    

