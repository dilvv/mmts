#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone


def status_file_path(base_dir=None):
    if base_dir is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "tmp_files", "runtime", "current_batch_status.json")


def _ensure_parent_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _timestamp():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_status(path=None, base_dir=None):
    status_path = path or status_file_path(base_dir=base_dir)
    if not os.path.exists(status_path):
        return {}
    with open(status_path, "r", encoding="utf-8") as fin:
        return json.load(fin)


def write_status(payload, path=None, base_dir=None):
    status_path = path or status_file_path(base_dir=base_dir)
    _ensure_parent_dir(status_path)
    payload = dict(payload)
    payload["updated_at"] = _timestamp()
    with open(status_path, "w", encoding="utf-8") as fout:
        json.dump(payload, fout, indent=2, sort_keys=True)
    return status_path


def update_status(patch, path=None, base_dir=None):
    current = read_status(path=path, base_dir=base_dir)
    current.update(patch)
    status = current.get("status")
    phase_state = current.get("phase_state")
    if "error_message" not in patch and status != "error" and phase_state != "error":
        current.pop("error_message", None)
    return write_status(current, path=path, base_dir=base_dir)
