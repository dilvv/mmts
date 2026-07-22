#!/usr/bin/env python3

import time
import random

stuck_code = random.randint(1,10) == 3

SLEEP_PERIOS = 0.5
def sleepPERIOD():
    time.sleep(SLEEP_PERIOS)

def fake_daq_client(stuckCODE):
    print('start daq client')
    sleepPERIOD()

    print('monitoring ...')
    sleepPERIOD()

    print('received cmd')
    sleepPERIOD()

    print('running cmd')
    sleepPERIOD()

    for runidx in range(100):
        print(f'[run] {runidx} .... laksjdfl kasjdlfkas jdfk')
        sleepPERIOD()

        if stuckCODE and runidx == 2:
            print('[Stuckinggggggg]')
            time.sleep(100)

    return

if __name__ == "__main__":
    #fake_daq_client(stuck_code)
    fake_daq_client(True)
    #fake_daq_client(False)
