#!/usr/bin/env python3
import logging
import sys

MMTS_SERVICE_EXAMPLE = '''
[Unit]
Description=MultiModuleTeststand web server
After=network.target nss-user-lookup.target

[Service]
Type=idle
User=pi
WorkingDirectory=/home/pi/.local/MultiModuleTeststandUI
Environment="PATH=/home/pi/.local/MultiModuleTeststandUI/.venv/bin:/home/pi/.local/MultiModuleTeststandUI/.venv/bin:/home/pi/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/games:/usr/games"
Environment="PYTHONPATH=/home/pi/.local/MultiModuleTeststandUI:"
Environment="LOG_LEVEL=INFO"
Environment="BASH_SCRIPT_FOLDER=/home/pi/.local/MultiModuleTeststandUI/scripts/task2_pedestalrun/"
Environment="AndrewModuleTestingGUI_BASE=/home/pi/.local/MultiModuleTeststandUI/external_packages/hgcal-module-testing-gui"
ExecStart=/home/pi/.local/MultiModuleTeststandUI/.venv/bin/python3 app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
'''

MMTS_SERVICE_TEMPLATE = '''
[Unit]
Description=MultiModuleTeststand web server
After=network.target nss-user-lookup.target

[Service]
Type=idle
User={USER}
WorkingDirectory={CURRENT_PATH}
Environment="PATH={CURRENT_PATH}/.venv/bin:{ORIG_PATH}"
Environment="PYTHONPATH={CURRENT_PATH}:{ORIG_PYTHONPATH}"
Environment="LOG_LEVEL=INFO"
Environment="BASH_SCRIPT_FOLDER={CURRENT_PATH}/scripts/task2_pedestalrun/"
Environment="AndrewModuleTestingGUI_BASE={CURRENT_PATH}/external_packages/hgcal-module-testing-gui"
ExecStart={CURRENT_PATH}/.venv/bin/python3 app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
'''
MMTS_SERVICE_TEMPLATE_VARS = {
        'CURRENT_PATH': None,
        'ORIG_PATH': None,
        'ORIG_PYTHONPATH': None,
        'USER': None,
        }




log = logging.getLogger(__name__)



if __name__ == '__main__':
    import os
    loglevel = os.environ.get('LOG_LEVEL', 'INFO') # DEBUG, INFO, WARNING
    DEBUG_MODE = True if loglevel == 'DEBUG' else False
    logLEVEL = getattr(logging, loglevel)
    logging.basicConfig(stream=sys.stdout,level=logLEVEL,
                        format=f'%(levelname)-7s%(filename)s#%(lineno)s %(funcName)s() >>> %(message)s',
                        datefmt='%H:%M:%S')

    var = lambda name: os.environ.get(name, '')
    print(f'[PATH] {var("PATH")}')
    print(f'[PWD] {var("PWD")}')
    print(f'[PYTHONPATH] {var("PYTHONPATH")}')

    MMTS_SERVICE_TEMPLATE_VARS = {
        'CURRENT_PATH': var("PWD"),
        'ORIG_PATH': var("PATH"),
        'ORIG_PYTHONPATH':var("PYTHONPATH"),
        'USER': var("USER"),
        }
    ofile = 'data/MMTS.service'
    with open(ofile, 'w') as fOUT:
        fOUT.write( MMTS_SERVICE_TEMPLATE.format(**MMTS_SERVICE_TEMPLATE_VARS) )
    log.info(f'[FileGenerated] service file "{ ofile }" exported')
    log.info(f'[ActionRequired] Put file to system by following commands:')
    log.info(f'[ActionRequired] > sudo mv {ofile} /etc/systemd/system/')
    log.info(f'[ActionRequired] > sudo systemctl daemon-reload')
    log.info(f'[ActionRequired] > sudo systemctl start MMTS.service')
    log.info(f'[ActionOptional] > sudo systemctl stop  MMTS.service')
    log.info(f'[ActionOptional] > journalctl -u MMTS.service')
