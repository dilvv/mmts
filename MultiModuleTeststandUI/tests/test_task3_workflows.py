#!/usr/bin/env python3
import hashlib
import os
import sys
import tempfile
import unittest
from unittest import mock

import yaml


UI_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.abspath(os.path.join(UI_ROOT, ".."))
PLC_ROOT = os.path.join(REPO_ROOT, "PLC_toolkits_mqtt_NTU")
sys.path.insert(0, UI_ROOT)
sys.path.insert(0, os.path.join(UI_ROOT, "scripts"))
sys.path.insert(0, PLC_ROOT)

from flask_apps.shared_state import (  # noqa: E402
    HardwareWorkflowGuard,
    classify_process_exit,
)
import run_full_mmts_batch as batch_runner  # noqa: E402
import run_selected_iv2_thermal_cycles as thermal_runner  # noqa: E402


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fin:
        for chunk in iter(lambda: fin.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ThermalCyclePlanTests(unittest.TestCase):
    def test_selected_cycle_plan(self):
        plan = thermal_runner.build_cycle_plan(5, [2, 4])
        self.assertEqual(plan, [
            {"cycle_number": 1, "cycles": 1, "idle_cold_min": 10, "runs_iv2": False},
            {"cycle_number": 2, "cycles": 1, "idle_cold_min": 59, "runs_iv2": True},
            {"cycle_number": 3, "cycles": 1, "idle_cold_min": 10, "runs_iv2": False},
            {"cycle_number": 4, "cycles": 1, "idle_cold_min": 59, "runs_iv2": True},
            {"cycle_number": 5, "cycles": 1, "idle_cold_min": 10, "runs_iv2": False},
        ])

    def test_runtime_config_does_not_modify_any_source_template(self):
        sources = [
            os.path.join(PLC_ROOT, "HMI_Control.yml"),
            os.path.join(PLC_ROOT, "HMI_Control_5cycle.yml"),
            os.path.join(PLC_ROOT, "HMI_Control_single_cycle.yml"),
        ]
        before = {path: file_hash(path) for path in sources}
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_path = os.path.join(tmpdir, "runtime.yml")
            thermal_runner.write_single_cycle_config(sources[2], runtime_path, 59)
            with open(runtime_path, "r", encoding="utf-8") as fin:
                runtime_cfg = yaml.safe_load(fin)
            self.assertEqual(runtime_cfg["experiment"]["cycles"], 1)
            self.assertEqual(runtime_cfg["experiment"]["idle_cold_min"], 59)
        after = {path: file_hash(path) for path in sources}
        self.assertEqual(before, after)

    def test_source_and_runtime_paths_must_differ(self):
        source = os.path.join(PLC_ROOT, "HMI_Control_single_cycle.yml")
        with self.assertRaises(ValueError):
            thermal_runner.write_single_cycle_config(source, source, 10)


class PlcStateTrackingTests(unittest.TestCase):
    def test_seen_five_then_first_new_poll_four_detects_transition(self):
        snapshot = {"plc_status_code": 4, "plc_status_text": "countdown cooling"}
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.object(
            batch_runner, "read_plc_snapshot", return_value=snapshot
        ):
            result = batch_runner.wait_for_status_transition(
                name="test_transition",
                client=object(),
                plc_cfg={},
                seen_code=5,
                target_code=4,
                status_file=os.path.join(tmpdir, "status.json"),
                timeout_seconds=1,
                poll_seconds=0,
                seen_already=True,
            )
        self.assertEqual(result["plc_status_code"], 4)

    def test_transient_standby_does_not_complete(self):
        tracker = batch_runner.StableStatusTracker(1, consecutive_samples=3)
        self.assertEqual(
            [tracker.observe(code) for code in (5, 1, 5)],
            [False, False, False],
        )
        self.assertEqual(
            [tracker.observe(code) for code in (1, 1, 1)],
            [False, False, True],
        )


class WorkflowGuardTests(unittest.TestCase):
    def test_only_one_hardware_workflow_can_own_guard(self):
        guard = HardwareWorkflowGuard()
        self.assertTrue(guard.try_acquire("AutoTest"))
        self.assertFalse(guard.try_acquire("ThermalCycle"))
        self.assertEqual(guard.owner, "AutoTest")
        self.assertTrue(guard.release("AutoTest"))
        self.assertTrue(guard.try_acquire("ThermalCycle"))

    def test_intentional_stop_is_not_error(self):
        self.assertEqual(classify_process_exit(-15, stop_requested=True), "stopped")
        self.assertEqual(classify_process_exit(-15, stop_requested=False), "error")
        self.assertEqual(classify_process_exit(0, stop_requested=False), "success")


if __name__ == "__main__":
    unittest.main()
