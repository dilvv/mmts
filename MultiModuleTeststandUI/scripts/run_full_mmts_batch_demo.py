#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import tempfile
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
    parser = argparse.ArgumentParser(
        description="Demo runner for one full MMTS batch with adjustable dewpoint and thermal-cycle parameters."
    )
    parser.add_argument(
        "-c",
        "--config",
        default=os.path.join(UI_ROOT, "data", "full_batch_demo.example.yml"),
        help="Path to demo batch configuration YAML.",
    )
    parser.add_argument(
        "--status-file",
        default=os.path.join(os.path.dirname(status_file_path(base_dir=UI_ROOT)), "current_batch_status_demo.json"),
        help="Path to shared demo batch status JSON.",
    )
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    parser.add_argument("--start-timeout-minutes", type=float, default=30.0)
    parser.add_argument("--transition-timeout-minutes", type=float, default=240.0)
    return parser.parse_args()


def actual_dew_point(raw_value):
    return 1.25 * raw_value - 5.0


def load_demo_config(path):
    with open(path, "r", encoding="utf-8") as fin:
        cfg = yaml.safe_load(fin)
    module_ids = cfg.get("module_ids", {})
    ordered_modules = {position: str(module_ids.get(position, "")).strip() for position in IV_POSITIONS}
    populated = {position: module_id for position, module_id in ordered_modules.items() if module_id}
    if not populated:
        raise ValueError("No module IDs found in demo configuration.")
    cfg["module_ids"] = ordered_modules
    cfg["populated_module_count"] = len(populated)
    return cfg


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


def run_command(command, cwd, status_file, stage, summary):
    update_status({
        "phase": stage,
        "phase_state": "running",
        "phase_summary": summary,
        "last_command": " ".join(command),
    }, path=status_file)
    process = subprocess.run(command, cwd=cwd, text=True)
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
        predicate=lambda snap: snap["min_dewpoint_C"] <= threshold,
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


def make_demo_hmi_config(base_filename, temp_output_path, cycle_cfg, dry_run):
    base_cfg = load_config(os.path.join(PLC_ROOT, base_filename))
    base_cfg["experiment"]["temp_high"] = float(cycle_cfg.get("temp_high", base_cfg["experiment"]["temp_high"]))
    base_cfg["experiment"]["temp_low"] = float(cycle_cfg.get("temp_low", base_cfg["experiment"]["temp_low"]))
    base_cfg["experiment"]["cycles"] = int(cycle_cfg.get("cycles", base_cfg["experiment"]["cycles"]))
    base_cfg["experiment"]["idle_warm_min"] = int(cycle_cfg.get("idle_warm_min", base_cfg["experiment"]["idle_warm_min"]))
    base_cfg["experiment"]["idle_cold_min"] = int(cycle_cfg.get("idle_cold_min", base_cfg["experiment"]["idle_cold_min"]))
    base_cfg["execution"]["dry_run"] = bool(dry_run)
    with open(temp_output_path, "w", encoding="utf-8") as fout:
        yaml.safe_dump(base_cfg, fout, sort_keys=False)
    return temp_output_path


def run_cycle(name, config_path, force_run, status_file):
    command = [sys.executable, "control_hmi.py", "-c", config_path]
    if force_run:
        command.append("-f")
    run_command(
        command,
        cwd=PLC_ROOT,
        status_file=status_file,
        stage=name,
        summary=f"Starting thermal cycle via {os.path.basename(config_path)}.",
    )


def main():
    args = parse_args()
    cfg = load_demo_config(args.config)
    plc_runtime_cfg = load_config(os.path.join(PLC_ROOT, "HMI_Control.yml"))["plc"]

    write_status({
        "runner": "run_full_mmts_batch_demo.py",
        "status": "starting",
        "started_at": now_iso(),
        "config_path": os.path.abspath(args.config),
        "phase": "startup",
        "phase_state": "starting",
        "phase_summary": "Preparing demo MMTS batch automation.",
        "module_ids": cfg["module_ids"],
        "populated_module_count": cfg["populated_module_count"],
        "demo_parameters": cfg.get("demo_controls", {}),
    }, path=args.status_file)

    client = create_client(plc_runtime_cfg)
    if not client or not client.get_connected():
        raise RuntimeError("Unable to connect to PLC for demo automation runner.")

    precheck = cfg.get("precheck", {})
    cycle_cfg = cfg.get("cycle_configs", {})
    iv_scans = cfg.get("iv_scans", {})
    demo_controls = cfg.get("demo_controls", {})
    dewpoint_threshold = float(demo_controls.get("dewpoint_threshold_C", -30.0))
    dry_run = bool(demo_controls.get("dry_run", True))
    force_run = bool(demo_controls.get("force_run", False))

    with tempfile.TemporaryDirectory(prefix="mmts_demo_", dir=os.path.join(UI_ROOT, "tmp_files", "runtime")) as temp_dir:
        first_cycle_cfg = make_demo_hmi_config(
            "HMI_Control.yml",
            os.path.join(temp_dir, "HMI_Control_demo_first.yml"),
            cycle_cfg["first_cycle"],
            dry_run=dry_run,
        )
        remaining_cycle_cfg = make_demo_hmi_config(
            "HMI_Control_5cycle.yml",
            os.path.join(temp_dir, "HMI_Control_demo_remaining.yml"),
            cycle_cfg["remaining_cycles"],
            dry_run=dry_run,
        )
        try:
            snapshot = read_plc_snapshot(client, plc_runtime_cfg)
            update_status({
                "status": "running",
                "phase": "precheck",
                "phase_state": "running",
                "phase_summary": "PLC connected. Running demo prechecks.",
                "plc": snapshot,
                "generated_hmi_configs": {
                    "first_cycle": first_cycle_cfg,
                    "remaining_cycles": remaining_cycle_cfg,
                },
            }, path=args.status_file)

            if precheck.get("require_standby", True) and snapshot["plc_status_code"] != 1:
                raise RuntimeError(f"PLC is not in standby. Current status: {snapshot}")

            wait_for_dewpoint(
                client=client,
                plc_cfg=plc_runtime_cfg,
                threshold=dewpoint_threshold,
                status_file=args.status_file,
                timeout_seconds=args.transition_timeout_minutes * 60.0,
                poll_seconds=args.poll_seconds,
            )

            run_iv_scan("iv1", iv_scans["iv1"], cfg["module_ids"], args.status_file)
            run_cycle("cycle1_start", first_cycle_cfg, force_run=force_run, status_file=args.status_file)
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

            run_cycle("cycle2to6_start", remaining_cycle_cfg, force_run=force_run, status_file=args.status_file)
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
                "phase_summary": "Demo MMTS batch completed.",
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
