#!/usr/bin/env python3
import threading


jobmode = ''
threading_lock = threading.Lock()
# threading_lock.acquire()
# threading_lock.release()
server_status = 'startup'
debug_mode = False
#job_stop_flag - threading.Event()
#job_thread = {'thread': None}

runidx = 0 ## used to identify run tag. It is always increased

DAQresult_current_modified = '' ## recorded state of os.path.getmtime(dirDAQresult)
