#!/usr/bin/env python3
import argparse
import os
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

from PythonTools.batch_status import status_file_path, update_status, write_status  # noqa: E402


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
        description="Run thermal cycles and automatically execute IV2 on selected cycles."
    )
    parser.add_argument("-c", "--config", required=True, help="Path to the generated workflow YAML.")
    parser.add_argument(
        "--status-file",
        default=status_file_path(base_dir=UI_ROOT),
        help="Path to the shared batch status JSON.",
    )
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    parser.add_argument("--start-timeout-minutes", type=float, default=30.0)
    parser.add_argument("--transition-timeout-minutes", type=float, default=1200.0)
    return parser.parse_args()


def validate_cycle_numbers(values, total_cycles):
    if not isinstance(total_cycles, int) or isinstance(total_cycles, bool):
        raise ValueError("total_cycles must be an integer.")
    if not 1 <= total_cycles <= 32767:
        raise ValueError("total_cycles must be between 1 and 32767.")
    if not isinstance(values, list):
        raise ValueError("iv2_cycles must be a list.")

    selected = []
    for value in values:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("Every IV2 cycle number must be an integer.")
        if not 1 <= value <= total_cycles:
            raise ValueError(f"IV2 cycle {value} is outside the range 1..{total_cycles}.")
        if value not in selected:
            selected.append(value)
    return sorted(selected)


def load_workflow_config(path):
    with open(path, "r", encoding="utf-8") as fin:
        cfg = yaml.safe_load(fin)
    if not isinstance(cfg, dict):
        raise ValueError("Thermal-cycle workflow config must be a mapping.")

    total_cycles = cfg.get("total_cycles")
    selected = validate_cycle_numbers(cfg.get("iv2_cycles", []), total_cycles)
    module_cfg = cfg.get("module_ids", {})
    module_ids = {
        position: str(module_cfg.get(position, "")).strip()
        for position in IV_POSITIONS
    }
    if selected and not any(module_ids.values()):
        raise ValueError("At least one module ID is required when IV2 cycles are selected.")

    iv2_scan = cfg.get("iv2_scan", {})
    for key in ("iteration", "temperature", "humidity", "max_voltage"):
        if selected and iv2_scan.get(key) in (None, ""):
            raise ValueError(f"Missing IV2 setting: {key}.")

    normal_hold = cfg.get("normal_cold_hold_minutes", 10)
    iv2_hold = cfg.get("iv2_cold_hold_minutes", 59)
    for name, value in (
        ("normal_cold_hold_minutes", normal_hold),
        ("iv2_cold_hold_minutes", iv2_hold),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 59:
            raise ValueError(f"{name} must be an integer between 1 and 59.")

    cfg["total_cycles"] = total_cycles
    cfg["iv2_cycles"] = selected
    cfg["module_ids"] = module_ids
    cfg["normal_cold_hold_minutes"] = normal_hold
    cfg["iv2_cold_hold_minutes"] = iv2_hold
    cfg["batch"] = str(cfg.get("batch") or datetime.now().strftime("%Y%m%d-%H%M%S"))
    return cfg


def write_single_cycle_config(base_path, output_path, cold_hold_minutes):
    with open(base_path, "r", encoding="utf-8") as fin:
        cycle_cfg = yaml.safe_load(fin)
    if not isinstance(cycle_cfg, dict) or not isinstance(cycle_cfg.get("experiment"), dict):
        raise ValueError("Base PLC config has no experiment mapping.")
    cycle_cfg["experiment"]["cycles"] = 1
    cycle_cfg["experiment"]["idle_cold_min"] = cold_hold_minutes
    with open(output_path, "w", encoding="utf-8") as fout:
        yaml.safe_dump(cycle_cfg, fout, sort_keys=False)


def estimate_cycle_seconds(cold_hold_minutes, warm_hold_minutes, completed_durations):
    fixed_hold_seconds = (cold_hold_minutes + warm_hold_minutes) * 60.0
    if not completed_durations:
        return fixed_hold_seconds
    return max(fixed_hold_seconds, sum(completed_durations) / len(completed_durations))


def estimate_next_iv2_seconds(
    current_cycle,
    current_elapsed_seconds,
    total_cycles,
    selected_cycles,
    normal_hold_minutes,
    iv2_hold_minutes,
    warm_hold_minutes,
    completed_durations,
    iv2_start_offsets,
):
    upcoming = sorted(
        cycle for cycle in selected_cycles
        if current_cycle <= cycle <= total_cycles
    )
    if not upcoming:
        return None, None
    target_cycle = upcoming[0]
    normal_cycle_seconds = estimate_cycle_seconds(
        normal_hold_minutes, warm_hold_minutes, completed_durations
    )
    selected_cycle_seconds = estimate_cycle_seconds(
        iv2_hold_minutes, warm_hold_minutes, completed_durations
    )
    if iv2_start_offsets:
        target_offset_seconds = sum(iv2_start_offsets) / len(iv2_start_offsets)
    else:
        motion_seconds = max(
            0.0,
            normal_cycle_seconds - ((normal_hold_minutes + warm_hold_minutes) * 60.0),
        )
        target_offset_seconds = (iv2_hold_minutes * 60.0) + (motion_seconds / 2.0)

    if target_cycle == current_cycle:
        return target_cycle, max(0, round(target_offset_seconds - current_elapsed_seconds))

    current_total = (
        selected_cycle_seconds
        if current_cycle in selected_cycles
        else normal_cycle_seconds
    )
    eta_seconds = max(0.0, current_total - current_elapsed_seconds)
    for cycle_number in range(current_cycle + 1, target_cycle):
        eta_seconds += (
            selected_cycle_seconds
            if cycle_number in selected_cycles
            else normal_cycle_seconds
        )
    return target_cycle, round(eta_seconds + target_offset_seconds)


def main():
    args = parse_args()
    cfg = load_workflow_config(args.config)
    from plc_io import create_client, load_config
    from run_full_mmts_batch import (
        IVInitializationError,
        read_plc_snapshot,
        run_cycle,
        run_iv_scan,
        wait_for_dewpoint,
        wait_for_status_code,
        wait_for_status_transition,
    )

    selected = set(cfg["iv2_cycles"])
    base_cycle_config = os.path.abspath(
        cfg.get("base_cycle_config") or os.path.join(PLC_ROOT, "HMI_Control_5cycle.yml")
    )
    with open(base_cycle_config, "r", encoding="utf-8") as fin:
        base_cycle_cfg = yaml.safe_load(fin)
    warm_hold_minutes = int(base_cycle_cfg["experiment"].get("idle_warm_min", 10))
    plc_runtime_cfg = load_config(base_cycle_config)["plc"]
    runtime_cycle_config = os.path.join(
        os.path.dirname(os.path.abspath(args.config)),
        "HMI_Control_thermal_cycle_current.yml",
    )

    write_status({
        "runner": "run_selected_iv2_thermal_cycles.py",
        "status": "starting",
        "started_at": now_iso(),
        "batch": cfg["batch"],
        "phase": "startup",
        "phase_state": "starting",
        "phase_summary": "Preparing selected-cycle IV2 thermal automation.",
        "module_ids": cfg["module_ids"],
        "thermal_cycle_count": cfg["total_cycles"],
        "iv2_cycles": cfg["iv2_cycles"],
    }, path=args.status_file)

    client = create_client(plc_runtime_cfg)
    if not client or not client.get_connected():
        raise RuntimeError("Unable to connect to PLC for thermal-cycle automation.")

    try:
        snapshot = read_plc_snapshot(client, plc_runtime_cfg)
        if snapshot["plc_status_code"] != 1:
            raise RuntimeError(f"PLC is not in standby. Current status: {snapshot}")

        dewpoint_max = cfg.get("dewpoint_max_C")
        if dewpoint_max is not None:
            wait_for_dewpoint(
                client=client,
                plc_cfg=plc_runtime_cfg,
                threshold=float(dewpoint_max),
                status_file=args.status_file,
                timeout_seconds=args.transition_timeout_minutes * 60.0,
                poll_seconds=args.poll_seconds,
            )

        completed_durations = []
        iv2_start_offsets = []
        skipped_iv2_cycles = []
        iv2_initialize_errors = {}
        for cycle_number in range(1, cfg["total_cycles"] + 1):
            runs_iv2 = cycle_number in selected
            cold_hold = (
                cfg["iv2_cold_hold_minutes"]
                if runs_iv2
                else cfg["normal_cold_hold_minutes"]
            )
            write_single_cycle_config(base_cycle_config, runtime_cycle_config, cold_hold)
            cycle_started_monotonic = time.monotonic()

            def timing_status():
                elapsed_seconds = round(time.monotonic() - cycle_started_monotonic)
                next_cycle, next_eta = estimate_next_iv2_seconds(
                    current_cycle=cycle_number,
                    current_elapsed_seconds=elapsed_seconds,
                    total_cycles=cfg["total_cycles"],
                    selected_cycles=selected,
                    normal_hold_minutes=cfg["normal_cold_hold_minutes"],
                    iv2_hold_minutes=cfg["iv2_cold_hold_minutes"],
                    warm_hold_minutes=warm_hold_minutes,
                    completed_durations=completed_durations,
                    iv2_start_offsets=iv2_start_offsets,
                )
                return {
                    "thermal_cycle_elapsed_seconds": elapsed_seconds,
                    "last_cycle_duration_seconds": (
                        round(completed_durations[-1]) if completed_durations else None
                    ),
                    "average_cycle_duration_seconds": (
                        round(sum(completed_durations) / len(completed_durations))
                        if completed_durations else None
                    ),
                    "next_iv2_cycle": next_cycle,
                    "next_iv2_eta_seconds": next_eta,
                }

            update_status({
                "status": "running",
                "phase": "thermal_cycle",
                "phase_state": "running",
                "phase_summary": (
                    f"Starting cycle {cycle_number}/{cfg['total_cycles']} "
                    f"with a {cold_hold}-minute low-temperature hold"
                    f"{' and automatic IV2' if runs_iv2 else ''}."
                ),
                "thermal_cycle_current": cycle_number,
                "thermal_cycle_count": cfg["total_cycles"],
                "iv2_cycles": cfg["iv2_cycles"],
                "current_cycle_runs_iv2": runs_iv2,
                **timing_status(),
            }, path=args.status_file)

            run_cycle(
                f"thermal_cycle_{cycle_number}_start",
                runtime_cycle_config,
                args.status_file,
            )
            wait_for_status_code(
                name=f"thermal_cycle_{cycle_number}_started",
                client=client,
                plc_cfg=plc_runtime_cfg,
                expected_code=5,
                status_file=args.status_file,
                timeout_seconds=args.start_timeout_minutes * 60.0,
                poll_seconds=args.poll_seconds,
                status_extra=timing_status,
            )

            if runs_iv2:
                wait_for_status_transition(
                    name=f"thermal_cycle_{cycle_number}_ready_for_iv2",
                    client=client,
                    plc_cfg=plc_runtime_cfg,
                    seen_code=5,
                    target_code=4,
                    status_file=args.status_file,
                    timeout_seconds=args.transition_timeout_minutes * 60.0,
                    poll_seconds=args.poll_seconds,
                    status_extra=timing_status,
                )
                iv2_start_offsets.append(time.monotonic() - cycle_started_monotonic)
                update_status({
                    "phase": "iv2",
                    "phase_state": "starting",
                    "phase_summary": f"Starting automatic IV2 during cycle {cycle_number}.",
                    **timing_status(),
                    "next_iv2_cycle": cycle_number,
                    "next_iv2_eta_seconds": 0,
                }, path=args.status_file)
                iv2_batch = f"{cfg['batch']}-C{cycle_number}"
                try:
                    run_iv_scan(
                        "iv2",
                        cfg["iv2_scan"],
                        cfg["module_ids"],
                        iv2_batch,
                        args.status_file,
                    )
                except IVInitializationError as exc:
                    skipped_iv2_cycles.append(cycle_number)
                    iv2_initialize_errors[str(cycle_number)] = str(exc)
                    update_status({
                        "status": "running",
                        "phase": "iv2",
                        "phase_state": "skipped",
                        "phase_summary": (
                            f"Skipped IV2 during cycle {cycle_number} because "
                            "IV hardware initialization failed; thermal cycling continues."
                        ),
                        "skipped_iv2_cycles": skipped_iv2_cycles,
                        "iv2_initialize_errors": iv2_initialize_errors,
                        **timing_status(),
                    }, path=args.status_file)

            wait_for_status_code(
                name=f"thermal_cycle_{cycle_number}_complete",
                client=client,
                plc_cfg=plc_runtime_cfg,
                expected_code=1,
                status_file=args.status_file,
                timeout_seconds=args.transition_timeout_minutes * 60.0,
                poll_seconds=args.poll_seconds,
                status_extra=timing_status,
            )
            completed_durations.append(time.monotonic() - cycle_started_monotonic)
            next_iv2_cycle, next_iv2_eta = estimate_next_iv2_seconds(
                current_cycle=cycle_number + 1,
                current_elapsed_seconds=0,
                total_cycles=cfg["total_cycles"],
                selected_cycles=selected,
                normal_hold_minutes=cfg["normal_cold_hold_minutes"],
                iv2_hold_minutes=cfg["iv2_cold_hold_minutes"],
                warm_hold_minutes=warm_hold_minutes,
                completed_durations=completed_durations,
                iv2_start_offsets=iv2_start_offsets,
            )
            update_status({
                "phase": "thermal_cycle",
                "phase_state": "cycle_completed",
                "phase_summary": (
                    f"Cycle {cycle_number}/{cfg['total_cycles']} completed in "
                    f"{round(completed_durations[-1])} seconds."
                ),
                "thermal_cycle_current": cycle_number,
                "thermal_cycle_elapsed_seconds": round(completed_durations[-1]),
                "last_cycle_duration_seconds": round(completed_durations[-1]),
                "average_cycle_duration_seconds": round(
                    sum(completed_durations) / len(completed_durations)
                ),
                "completed_cycle_durations_seconds": [
                    round(duration) for duration in completed_durations
                ],
                "skipped_iv2_cycles": skipped_iv2_cycles,
                "iv2_initialize_errors": iv2_initialize_errors,
                "next_iv2_cycle": next_iv2_cycle,
                "next_iv2_eta_seconds": next_iv2_eta,
            }, path=args.status_file)

        update_status({
            "status": "completed",
            "phase": "done",
            "phase_state": "completed",
            "phase_summary": (
                f"Completed {cfg['total_cycles']} thermal cycles; "
                f"IV2 completed on {len(selected) - len(skipped_iv2_cycles)} selected "
                f"cycle(s) and was skipped on {len(skipped_iv2_cycles)} cycle(s)."
            ),
            "finished_at": now_iso(),
            "skipped_iv2_cycles": skipped_iv2_cycles,
            "iv2_initialize_errors": iv2_initialize_errors,
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
        try:
            if os.path.isfile(runtime_cycle_config):
                os.remove(runtime_cycle_config)
        except OSError:
            pass


if __name__ == "__main__":
    main()
