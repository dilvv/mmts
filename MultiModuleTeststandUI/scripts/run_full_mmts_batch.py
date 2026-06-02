#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import yaml

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
UI_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_ROOT = os.path.abspath(os.path.join(UI_ROOT, ".."))
PLC_ROOT = os.path.join(REPO_ROOT, "PLC_toolkits_mqtt_NTU")
sys.path.insert(0, UI_ROOT)
sys.path.insert(0, PLC_ROOT)

from PythonTools.batch_status import status_file_path, write_status, update_status  # noqa: E402
from plc_io import create_client, load_config, read_sensor_real, system_status  # noqa: E402


IV_POSITIONS = [
    "1L", "1C", "1R",
    "2L", "2C", "2R",
    "3L", "3C", "3R",
    "4L", "4C", "4R",
    "5L", "5C", "5R",
    "6L", "6C", "6R",
    "7L", "7C", "7R",
    "8L", "8C", "8R",
]


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args():
    parser = argparse.ArgumentParser(description="Run one full MMTS batch automatically while the GUI remains open for monitoring.")
    parser.add_argument("-c", "--config", default=os.path.join(UI_ROOT, "data", "full_batch_config.example.yml"),
                        help="Path to batch configuration YAML.")
    parser.add_argument("--status-file", default=status_file_path(base_dir=UI_ROOT),
                        help="Path to shared batch status JSON.")
    parser.add_argument("--poll-seconds", type=float, default=10.0,
                        help="Polling interval for PLC state transitions.")
    parser.add_argument("--start-timeout-minutes", type=float, default=30.0,
                        help="Timeout while waiting for a cycle to leave standby.")
    parser.add_argument("--transition-timeout-minutes", type=float, default=1200.0,
                        help="Timeout for major PLC state transitions.")
    return parser.parse_args()


def actual_dew_point(raw_value):
    return 1.25 * raw_value - 5.0


def load_batch_config(path):
    with open(path, "r", encoding="utf-8") as fin:
        cfg = yaml.safe_load(fin)
    module_ids = cfg.get("module_ids", {})
    ordered_modules = {position: str(module_ids.get(position, "")).strip() for position in IV_POSITIONS}
    populated_modules = {position: module_id for position, module_id in ordered_modules.items() if module_id}
    if not populated_modules:
        raise ValueError("No module IDs found in batch configuration.")
    cfg["module_ids"] = ordered_modules
    cfg["populated_module_count"] = len(populated_modules)
    return cfg


def status_summary(code, text, extra=None):
    payload = {"plc_status_code": code, "plc_status_text": text}
    if extra:
        payload.update(extra)
    return payload


def read_plc_snapshot(client, plc_cfg):
    status_code, status_text = system_status(client)
    dew1 = actual_dew_point(read_sensor_real(client, plc_cfg["db_number"], 314))
    dew2 = actual_dew_point(read_sensor_real(client, plc_cfg["db_number"], 356))
    return {
        "plc_status_code": status_code,
        "plc_status_text": status_text,
        "dewpoint_1_C": round(dew1, 2),
        "dewpoint_2_C": round(dew2, 2),
        "min_dewpoint_C": round(min(dew1, dew2), 2),
    }


def run_command(command, cwd, status_file, stage, summary, env=None):
    update_status({
        "phase": stage,
        "phase_state": "running",
        "phase_summary": summary,
        "last_command": " ".join(command),
    }, path=status_file)
    process = subprocess.run(command, cwd=cwd, text=True, env=env)
    if process.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {process.returncode}: {' '.join(command)}")


def build_iv_command(scan_cfg, module_ids):
    command = ["make", "-f", "makefile_task3", "run"]
    for position, module_id in module_ids.items():
        if module_id:
            command.append(f"moduleID{position}={module_id}")
    command.append(f"currentTEMPERATURE={scan_cfg['temperature']}")
    command.append(f"currentHUMIDITY={scan_cfg['humidity']}")
    command.append(f"maxVOLTAGE={scan_cfg['max_voltage']}")
    return command


def run_iv_scan(scan_name, scan_cfg, module_ids, status_file):
    run_command(
        ["make", "-f", "makefile_task3", "initialize"],
        cwd=UI_ROOT,
        status_file=status_file,
        stage=f"{scan_name}_initialize",
        summary=f"Initializing IV hardware for {scan_name}.",
    )
    run_command(
        build_iv_command(scan_cfg, module_ids),
        cwd=UI_ROOT,
        status_file=status_file,
        stage=scan_name,
        summary=f"Running {scan_name} at {scan_cfg['temperature']} C / {scan_cfg['humidity']} RH.",
    )
    update_status({
        "phase": scan_name,
        "phase_state": "completed",
        "phase_summary": f"{scan_name} completed.",
    }, path=status_file)


def wait_for_condition(name, status_file, client, plc_cfg, predicate, timeout_seconds, poll_seconds):
    deadline = time.time() + timeout_seconds
    last_snapshot = None
    while time.time() < deadline:
        snapshot = read_plc_snapshot(client, plc_cfg)
        last_snapshot = snapshot
        update_status({
            "phase": name,
            "phase_state": "waiting",
            "phase_summary": f"Waiting for {name}.",
            "plc": snapshot,
        }, path=status_file)
        if predicate(snapshot):
            return snapshot
        time.sleep(poll_seconds)
    raise TimeoutError(f"Timed out while waiting for {name}. Last PLC snapshot: {last_snapshot}")


def wait_for_dewpoint(client, plc_cfg, threshold, status_file, timeout_seconds, poll_seconds):
    return wait_for_condition(
        name="dewpoint_ready",
        status_file=status_file,
        client=client,
        plc_cfg=plc_cfg,
        predicate=lambda snap: snap["dewpoint_1_C"] < threshold and snap["dewpoint_2_C"] < threshold,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )


def wait_for_status_code(name, client, plc_cfg, expected_code, status_file, timeout_seconds, poll_seconds):
    return wait_for_condition(
        name=name,
        status_file=status_file,
        client=client,
        plc_cfg=plc_cfg,
        predicate=lambda snap: snap["plc_status_code"] == expected_code,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )


def wait_for_status_transition(name, client, plc_cfg, seen_code, target_code, status_file, timeout_seconds, poll_seconds):
    deadline = time.time() + timeout_seconds
    observed_seen = False
    last_snapshot = None
    while time.time() < deadline:
        snapshot = read_plc_snapshot(client, plc_cfg)
        last_snapshot = snapshot
        if snapshot["plc_status_code"] == seen_code:
            observed_seen = True
        update_status({
            "phase": name,
            "phase_state": "waiting",
            "phase_summary": f"Waiting for PLC transition {seen_code} -> {target_code}.",
            "plc": snapshot,
        }, path=status_file)
        if observed_seen and snapshot["plc_status_code"] == target_code:
            return snapshot
        time.sleep(poll_seconds)
    raise TimeoutError(f"Timed out while waiting for PLC transition {seen_code} -> {target_code}. Last PLC snapshot: {last_snapshot}")


def run_cycle(name, config_filename, status_file):
    run_command(
        [sys.executable, "control_hmi.py", "-c", config_filename, "-f"],
        cwd=PLC_ROOT,
        status_file=status_file,
        stage=name,
        summary=f"Starting thermal cycle via {config_filename}.",
    )


def main():
    args = parse_args()
    cfg = load_batch_config(args.config)
    plc_runtime_cfg = load_config(os.path.join(PLC_ROOT, "HMI_Control.yml"))["plc"]

    write_status({
        "runner": "run_full_mmts_batch.py",
        "status": "starting",
        "started_at": now_iso(),
        "config_path": os.path.abspath(args.config),
        "phase": "startup",
        "phase_state": "starting",
        "phase_summary": "Preparing full MMTS batch automation.",
        "module_ids": cfg["module_ids"],
        "populated_module_count": cfg["populated_module_count"],
    }, path=args.status_file)

    client = create_client(plc_runtime_cfg)
    if not client or not client.get_connected():
        raise RuntimeError("Unable to connect to PLC for automation runner.")

    precheck = cfg.get("precheck", {})
    cycle_cfg = cfg.get("cycle_configs", {})
    iv_scans = cfg.get("iv_scans", {})

    try:
        snapshot = read_plc_snapshot(client, plc_runtime_cfg)
        update_status({
            "status": "running",
            "phase": "precheck",
            "phase_state": "running",
            "phase_summary": "PLC connected. Running prechecks.",
            "plc": snapshot,
        }, path=args.status_file)

        if precheck.get("require_standby", True) and snapshot["plc_status_code"] != 1:
            raise RuntimeError(f"PLC is not in standby. Current status: {snapshot}")

        run_iv_scan("iv1", iv_scans["iv1"], cfg["module_ids"], args.status_file)

        if precheck.get("dewpoint_max_C") is not None:
            wait_for_dewpoint(
                client=client,
                plc_cfg=plc_runtime_cfg,
                threshold=float(precheck["dewpoint_max_C"]),
                status_file=args.status_file,
                timeout_seconds=args.transition_timeout_minutes * 60.0,
                poll_seconds=args.poll_seconds,
            )

        run_cycle("cycle1_start", cycle_cfg.get("first_cycle", "HMI_Control.yml"), args.status_file)
        wait_for_status_code(
            name="cycle1_started",
            client=client,
            plc_cfg=plc_runtime_cfg,
            expected_code=5,
            status_file=args.status_file,
            timeout_seconds=args.start_timeout_minutes * 60.0,
            poll_seconds=args.poll_seconds,
        )
        wait_for_status_transition(
            name="cycle1_ready_for_iv2",
            client=client,
            plc_cfg=plc_runtime_cfg,
            seen_code=5,
            target_code=4,
            status_file=args.status_file,
            timeout_seconds=args.transition_timeout_minutes * 60.0,
            poll_seconds=args.poll_seconds,
        )

        run_iv_scan("iv2", iv_scans["iv2"], cfg["module_ids"], args.status_file)
        wait_for_status_code(
            name="cycle1_complete",
            client=client,
            plc_cfg=plc_runtime_cfg,
            expected_code=1,
            status_file=args.status_file,
            timeout_seconds=args.transition_timeout_minutes * 60.0,
            poll_seconds=args.poll_seconds,
        )

        run_cycle("cycle2to6_start", cycle_cfg.get("remaining_cycles", "HMI_Control_5cycle.yml"), args.status_file)
        wait_for_status_code(
            name="cycle2to6_started",
            client=client,
            plc_cfg=plc_runtime_cfg,
            expected_code=5,
            status_file=args.status_file,
            timeout_seconds=args.start_timeout_minutes * 60.0,
            poll_seconds=args.poll_seconds,
        )
        wait_for_status_code(
            name="cycle2to6_complete",
            client=client,
            plc_cfg=plc_runtime_cfg,
            expected_code=1,
            status_file=args.status_file,
            timeout_seconds=args.transition_timeout_minutes * 60.0,
            poll_seconds=args.poll_seconds,
        )

        run_iv_scan("iv3", iv_scans["iv3"], cfg["module_ids"], args.status_file)
        update_status({
            "status": "completed",
            "phase": "done",
            "phase_state": "completed",
            "phase_summary": "Full MMTS batch completed.",
            "finished_at": now_iso(),
        }, path=args.status_file)
    except Exception as exc:
        update_status({
            "status": "error",
            "phase_state": "error",
            "error_message": str(exc),
            "finished_at": now_iso(),
        }, path=args.status_file)
        raise
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
