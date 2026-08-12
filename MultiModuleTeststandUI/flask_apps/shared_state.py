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


class HardwareWorkflowGuard:
    """Process-local ownership guard for workflows that use shared hardware."""

    def __init__(self):
        self._lock = threading.Lock()
        self._owner = None

    def try_acquire(self, owner):
        with self._lock:
            if self._owner is not None:
                return False
            self._owner = owner
            return True

    def release(self, owner):
        with self._lock:
            if self._owner != owner:
                return False
            self._owner = None
            return True

    @property
    def owner(self):
        with self._lock:
            return self._owner


def classify_process_exit(returncode, stop_requested=False):
    """Classify an exit without treating an operator-requested stop as a crash."""
    if stop_requested:
        return 'stopped'
    return 'success' if returncode == 0 else 'error'


hardware_workflow_guard = HardwareWorkflowGuard()
