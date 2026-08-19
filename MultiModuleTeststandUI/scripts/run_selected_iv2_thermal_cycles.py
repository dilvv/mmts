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
    parser.add_argument("--start-validation-timeout-seconds", type=float, default=60.0)
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
    if not any(module_ids.values()):
        raise ValueError("At least one module ID is required for the initial IV1 scan.")

    iv1_scan = cfg.get("iv1_scan", {})
    for key in ("iteration", "temperature", "humidity", "max_voltage"):
        if iv1_scan.get(key) in (None, ""):
            raise ValueError(f"Missing IV1 setting: {key}.")

    iv2_scan = cfg.get("iv2_scan", {})
    for key in ("iteration", "temperature", "humidity", "max_voltage"):
        if selected and iv2_scan.get(key) in (None, ""):
            raise ValueError(f"Missing IV2 setting: {key}.")

    iv3_scan = cfg.get("iv3_scan", {})
    for key in ("iteration", "temperature", "humidity", "max_voltage"):
        if iv3_scan.get(key) in (None, ""):
            raise ValueError(f"Missing IV3 setting: {key}.")

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


def write_segment_config(base_path, output_path, cycle_count, cold_hold_minutes):
    if os.path.abspath(base_path) == os.path.abspath(output_path):
        raise ValueError("Runtime PLC config must not overwrite its source template.")
    if not isinstance(cycle_count, int) or isinstance(cycle_count, bool) or cycle_count < 1:
        raise ValueError("Segment cycle count must be a positive integer.")
    with open(base_path, "r", encoding="utf-8") as fin:
        cycle_cfg = yaml.safe_load(fin)
    if not isinstance(cycle_cfg, dict) or not isinstance(cycle_cfg.get("experiment"), dict):
        raise ValueError("Base PLC config has no experiment mapping.")
    cycle_cfg["experiment"]["cycles"] = cycle_count
    cycle_cfg["experiment"]["idle_cold_min"] = cold_hold_minutes
    with open(output_path, "w", encoding="utf-8") as fout:
        yaml.safe_dump(cycle_cfg, fout, sort_keys=False)


def write_single_cycle_config(base_path, output_path, cold_hold_minutes):
    """Compatibility wrapper for callers/tests that need one PLC cycle."""
    write_segment_config(base_path, output_path, 1, cold_hold_minutes)


def build_segment_plan(total_cycles, selected_cycles, normal_hold_minutes=10, iv2_hold_minutes=59):
    selected = validate_cycle_numbers(list(selected_cycles), total_cycles)
    segments = []
    next_cycle = 1

    def append_segment(start_cycle, end_cycle, idle_cold_min, runs_iv2):
        segments.append({
            "segment_number": len(segments) + 1,
            "start_cycle": start_cycle,
            "end_cycle": end_cycle,
            "cycles": end_cycle - start_cycle + 1,
            "idle_cold_min": idle_cold_min,
            "runs_iv2": runs_iv2,
            "iv2_cycle": start_cycle if runs_iv2 else None,
        })

    for iv2_cycle in selected:
        if next_cycle < iv2_cycle:
            append_segment(next_cycle, iv2_cycle - 1, normal_hold_minutes, False)
        append_segment(iv2_cycle, iv2_cycle, iv2_hold_minutes, True)
        next_cycle = iv2_cycle + 1
    if next_cycle <= total_cycles:
        append_segment(next_cycle, total_cycles, normal_hold_minutes, False)
    return segments


def runtime_segment_config_path(workflow_config_path, segment_number):
    base_path = os.path.splitext(os.path.abspath(workflow_config_path))[0]
    return f"{base_path}.segment-{segment_number:03d}.yml"


class ThermalStartError(RuntimeError):
    """Raised when two complete PLC START invocations fail state validation."""


def start_thermal_segment_with_validation(
    name,
    config_filename,
    status_file,
    client,
    plc_cfg,
    validation_timeout_seconds=60.0,
    poll_seconds=2.0,
    status_extra=None,
    run_cycle_func=None,
    wait_for_condition_func=None,
):
    from run_full_mmts_batch import PLCCommunicationError
    if run_cycle_func is None or wait_for_condition_func is None:
        from run_full_mmts_batch import run_cycle, wait_for_condition
        run_cycle_func = run_cycle_func or run_cycle
        wait_for_condition_func = wait_for_condition_func or wait_for_condition

    failure_reasons = []
    for attempt in (1, 2):
        update_status({
            "phase": f"{name}_start_attempt_{attempt}",
            "phase_state": "starting",
            "phase_summary": f"Starting thermal segment; complete START attempt {attempt}/2.",
            "thermal_start_attempt": attempt,
        }, path=status_file)
        try:
            run_cycle_func(
                f"{name}_start_attempt_{attempt}",
                config_filename,
                status_file,
            )
            snapshot = wait_for_condition_func(
                name=f"{name}_start_validation_{attempt}",
                status_file=status_file,
                client=client,
                plc_cfg=plc_cfg,
                predicate=lambda snap: snap["plc_status_code"] in (4, 5),
                timeout_seconds=validation_timeout_seconds,
                poll_seconds=poll_seconds,
                status_extra=status_extra,
            )
            update_status({
                "phase": f"{name}_started",
                "phase_state": "running",
                "phase_summary": (
                    f"Thermal START attempt {attempt} validated with PLC status "
                    f"{snapshot['plc_status_code']}."
                ),
                "thermal_start_attempt": attempt,
            }, path=status_file)
            return snapshot
        except PLCCommunicationError:
            raise
        except TimeoutError as exc:
            reason = f"Thermal START attempt {attempt} failed validation: {exc}"
        except RuntimeError as exc:
            reason = f"Thermal START attempt {attempt} command failed: {exc}"

        failure_reasons.append(reason)
        print(f"[ThermalStartWarning] {reason}", flush=True)
        update_status({
            "phase": f"{name}_start_attempt_{attempt}",
            "phase_state": "retrying" if attempt == 1 else "error",
            "phase_summary": reason,
            "thermal_start_attempt": attempt,
        }, path=status_file)

    raise ThermalStartError(
        f"Thermal segment failed to start after 2 complete attempts. "
        f"{' | '.join(failure_reasons)}"
    )


def main():
    args = parse_args()
    cfg = load_workflow_config(args.config)
    from plc_io import load_config
    from run_full_mmts_batch import (
        IVInitializationError,
        ReliablePLCSnapshotReader,
        run_cycle,
        run_iv_scan,
        wait_for_dewpoint,
        wait_for_stable_status_code,
        wait_for_status_transition,
    )

    selected = set(cfg["iv2_cycles"])
    segment_plan = build_segment_plan(
        cfg["total_cycles"],
        cfg["iv2_cycles"],
        normal_hold_minutes=cfg["normal_cold_hold_minutes"],
        iv2_hold_minutes=cfg["iv2_cold_hold_minutes"],
    )
    base_cycle_config = os.path.abspath(
        cfg.get("base_cycle_config") or os.path.join(PLC_ROOT, "HMI_Control_single_cycle.yml")
    )
    plc_runtime_cfg = load_config(base_cycle_config)["plc"]

    write_status({
        "runner": "run_selected_iv2_thermal_cycles.py",
        "status": "starting",
        "started_at": now_iso(),
        "batch": cfg["batch"],
        "phase": "startup",
        "phase_state": "starting",
        "workflow_type": "thermal_cycle",
        "thermal_stop_available": True,
        "phase_summary": "Preparing IV1, segmented thermal automation, selected IV2, and IV3.",
        "module_ids": cfg["module_ids"],
        "thermal_cycle_count": cfg["total_cycles"],
        "thermal_segment_count": len(segment_plan),
        "thermal_completed_cycles": 0,
        "iv2_cycles": cfg["iv2_cycles"],
    }, path=args.status_file)

    client = ReliablePLCSnapshotReader(plc_runtime_cfg)

    runtime_segment_configs = []
    thermal_program_active = False
    try:
        run_iv_scan(
            "iv1",
            cfg["iv1_scan"],
            cfg["module_ids"],
            cfg["batch"],
            args.status_file,
        )

        snapshot = client.read()
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

        completed_segment_durations = []
        completed_logical_cycles = 0
        skipped_iv2_cycles = []
        iv2_initialize_errors = {}

        for segment in segment_plan:
            segment_number = segment["segment_number"]
            start_cycle = segment["start_cycle"]
            end_cycle = segment["end_cycle"]
            runs_iv2 = segment["runs_iv2"]
            cold_hold = segment["idle_cold_min"]
            runtime_segment_config = runtime_segment_config_path(args.config, segment_number)
            runtime_segment_configs.append(runtime_segment_config)
            write_segment_config(
                base_cycle_config,
                runtime_segment_config,
                segment["cycles"],
                cold_hold,
            )
            segment_started_monotonic = time.monotonic()
            segment_range = (
                str(start_cycle) if start_cycle == end_cycle
                else f"{start_cycle}-{end_cycle}"
            )

            def timing_status():
                elapsed_seconds = round(time.monotonic() - segment_started_monotonic)
                next_iv2_cycle = next(
                    (
                        cycle for cycle in sorted(selected)
                        if cycle > completed_logical_cycles
                    ),
                    None,
                )
                return {
                    "thermal_segment_elapsed_seconds": elapsed_seconds,
                    "last_segment_duration_seconds": (
                        round(completed_segment_durations[-1])
                        if completed_segment_durations else None
                    ),
                    "average_segment_duration_seconds": (
                        round(
                            sum(completed_segment_durations)
                            / len(completed_segment_durations)
                        )
                        if completed_segment_durations else None
                    ),
                    "next_iv2_cycle": next_iv2_cycle,
                    "next_iv2_eta_seconds": None,
                }

            update_status({
                "status": "running",
                "phase": f"thermal_segment_{segment_number}",
                "phase_state": "starting",
                "phase_summary": (
                    f"Starting segment {segment_number}/{len(segment_plan)}: logical cycles "
                    f"{segment_range} of {cfg['total_cycles']}; PLC cycles={segment['cycles']}, "
                    f"cold hold={cold_hold} minutes"
                    f"{' with automatic IV2' if runs_iv2 else ''}."
                ),
                "thermal_cycle_count": cfg["total_cycles"],
                "thermal_segment_index": segment_number,
                "thermal_segment_count": len(segment_plan),
                "thermal_segment_start_cycle": start_cycle,
                "thermal_segment_end_cycle": end_cycle,
                "thermal_segment_cycles": segment["cycles"],
                "thermal_completed_cycles": completed_logical_cycles,
                "iv2_cycles": cfg["iv2_cycles"],
                "current_segment_runs_iv2": runs_iv2,
                **timing_status(),
            }, path=args.status_file)

            thermal_program_active = True
            start_thermal_segment_with_validation(
                name=f"thermal_segment_{segment_number}",
                config_filename=runtime_segment_config,
                status_file=args.status_file,
                client=client,
                plc_cfg=plc_runtime_cfg,
                validation_timeout_seconds=args.start_validation_timeout_seconds,
                poll_seconds=args.poll_seconds,
                status_extra=timing_status,
                run_cycle_func=run_cycle,
            )

            if runs_iv2:
                cycle_number = segment["iv2_cycle"]
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
                    seen_already=True,
                )
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

            wait_for_stable_status_code(
                name=f"thermal_segment_{segment_number}_complete",
                client=client,
                plc_cfg=plc_runtime_cfg,
                expected_code=1,
                status_file=args.status_file,
                timeout_seconds=(
                    args.transition_timeout_minutes * 60.0 * segment["cycles"]
                ),
                poll_seconds=args.poll_seconds,
                consecutive_samples=3,
                activity_observed=True,
                status_extra=timing_status,
            )
            thermal_program_active = False
            completed_segment_durations.append(
                time.monotonic() - segment_started_monotonic
            )
            completed_logical_cycles = end_cycle
            next_iv2_cycle = next(
                (cycle for cycle in sorted(selected) if cycle > completed_logical_cycles),
                None,
            )
            update_status({
                "phase": f"thermal_segment_{segment_number}",
                "phase_state": "segment_completed",
                "phase_summary": (
                    f"Segment {segment_number}/{len(segment_plan)} completed; logical cycles "
                    f"{segment_range} are complete ({completed_logical_cycles}/"
                    f"{cfg['total_cycles']}) in "
                    f"{round(completed_segment_durations[-1])} seconds."
                ),
                "thermal_completed_cycles": completed_logical_cycles,
                "thermal_segment_elapsed_seconds": round(completed_segment_durations[-1]),
                "last_segment_duration_seconds": round(completed_segment_durations[-1]),
                "average_segment_duration_seconds": round(
                    sum(completed_segment_durations) / len(completed_segment_durations)
                ),
                "completed_segment_durations_seconds": [
                    round(duration) for duration in completed_segment_durations
                ],
                "skipped_iv2_cycles": skipped_iv2_cycles,
                "iv2_initialize_errors": iv2_initialize_errors,
                "next_iv2_cycle": next_iv2_cycle,
                "next_iv2_eta_seconds": None,
            }, path=args.status_file)

        update_status({
            "status": "running",
            "phase": "iv3",
            "phase_state": "starting",
            "thermal_stop_available": False,
            "phase_summary": "All thermal segments completed in stable Standby; starting final IV3.",
        }, path=args.status_file)
        run_iv_scan(
            "iv3",
            cfg["iv3_scan"],
            cfg["module_ids"],
            cfg["batch"],
            args.status_file,
        )

        update_status({
            "status": "completed",
            "phase": "done",
            "phase_state": "completed",
            "thermal_stop_available": False,
            "phase_summary": (
                f"Completed {cfg['total_cycles']} thermal cycles; "
                f"IV2 completed on {len(selected) - len(skipped_iv2_cycles)} selected "
                f"cycle(s), skipped on {len(skipped_iv2_cycles)} cycle(s), and final IV3 completed."
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
            "thermal_stop_available": thermal_program_active,
            "finished_at": now_iso(),
        }, path=args.status_file)
        raise
    finally:
        client.disconnect()
        for runtime_segment_config in runtime_segment_configs:
            try:
                if os.path.isfile(runtime_segment_config):
                    os.remove(runtime_segment_config)
            except OSError:
                pass


if __name__ == "__main__":
    main()
