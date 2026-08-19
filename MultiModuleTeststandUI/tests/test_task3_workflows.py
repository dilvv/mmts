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
from flask_apps import app_task3  # noqa: E402


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fin:
        for chunk in iter(lambda: fin.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ThermalCyclePlanTests(unittest.TestCase):
    def test_segments_20_with_iv2_10(self):
        plan = thermal_runner.build_segment_plan(20, [10])
        self.assertEqual(plan, [
            {"segment_number": 1, "start_cycle": 1, "end_cycle": 9, "cycles": 9,
             "idle_cold_min": 10, "runs_iv2": False, "iv2_cycle": None},
            {"segment_number": 2, "start_cycle": 10, "end_cycle": 10, "cycles": 1,
             "idle_cold_min": 59, "runs_iv2": True, "iv2_cycle": 10},
            {"segment_number": 3, "start_cycle": 11, "end_cycle": 20, "cycles": 10,
             "idle_cold_min": 10, "runs_iv2": False, "iv2_cycle": None},
        ])

    def test_segments_20_with_iv2_5_10_15(self):
        plan = thermal_runner.build_segment_plan(20, [5, 10, 15])
        self.assertEqual(
            [(item["start_cycle"], item["end_cycle"], item["cycles"],
              item["idle_cold_min"], item["runs_iv2"]) for item in plan],
            [
                (1, 4, 4, 10, False),
                (5, 5, 1, 59, True),
                (6, 9, 4, 10, False),
                (10, 10, 1, 59, True),
                (11, 14, 4, 10, False),
                (15, 15, 1, 59, True),
                (16, 20, 5, 10, False),
            ],
        )

    def test_adjacent_iv2_cycles_remain_separate_segments(self):
        plan = thermal_runner.build_segment_plan(5, [2, 3])
        self.assertEqual(
            [(item["start_cycle"], item["end_cycle"], item["cycles"],
              item["idle_cold_min"], item["runs_iv2"]) for item in plan],
            [
                (1, 1, 1, 10, False),
                (2, 2, 1, 59, True),
                (3, 3, 1, 59, True),
                (4, 5, 2, 10, False),
            ],
        )

    def test_runtime_config_does_not_modify_any_source_template(self):
        sources = [
            os.path.join(PLC_ROOT, "HMI_Control.yml"),
            os.path.join(PLC_ROOT, "HMI_Control_5cycle.yml"),
            os.path.join(PLC_ROOT, "HMI_Control_single_cycle.yml"),
        ]
        before = {path: file_hash(path) for path in sources}
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_path = os.path.join(tmpdir, "runtime.yml")
            thermal_runner.write_segment_config(sources[2], runtime_path, 9, 10)
            with open(runtime_path, "r", encoding="utf-8") as fin:
                runtime_cfg = yaml.safe_load(fin)
            self.assertEqual(runtime_cfg["experiment"]["cycles"], 9)
            self.assertEqual(runtime_cfg["experiment"]["idle_cold_min"], 10)
        after = {path: file_hash(path) for path in sources}
        self.assertEqual(before, after)

    def test_source_and_runtime_paths_must_differ(self):
        source = os.path.join(PLC_ROOT, "HMI_Control_single_cycle.yml")
        with self.assertRaises(ValueError):
            thermal_runner.write_segment_config(source, source, 1, 10)

    def test_each_segment_has_a_unique_runtime_config_outside_plc_toolkit(self):
        workflow_path = os.path.join(UI_ROOT, "tmp_files", "runtime", "workflow.yml")
        first = thermal_runner.runtime_segment_config_path(workflow_path, 1)
        second = thermal_runner.runtime_segment_config_path(workflow_path, 2)
        self.assertNotEqual(first, second)
        self.assertFalse(first.startswith(os.path.abspath(PLC_ROOT) + os.sep))
        self.assertTrue(first.endswith(".segment-001.yml"))


class ThermalStartValidationTests(unittest.TestCase):
    def call_start(self, starter, waiter):
        with mock.patch.object(thermal_runner, "update_status"):
            return thermal_runner.start_thermal_segment_with_validation(
                name="segment_1",
                config_filename="runtime.yml",
                status_file="status.json",
                client=object(),
                plc_cfg={},
                validation_timeout_seconds=60,
                poll_seconds=0,
                run_cycle_func=starter,
                wait_for_condition_func=waiter,
            )

    def test_first_complete_start_attempt_succeeds(self):
        starter = mock.Mock(return_value=None)

        def waiter(**kwargs):
            self.assertFalse(kwargs["predicate"]({"plc_status_code": 1}))
            self.assertTrue(kwargs["predicate"]({"plc_status_code": 5}))
            return {"plc_status_code": 5}

        result = self.call_start(starter, mock.Mock(side_effect=waiter))
        self.assertEqual(result["plc_status_code"], 5)
        self.assertEqual(starter.call_count, 1)

    def test_second_complete_start_attempt_succeeds(self):
        starter = mock.Mock(return_value=None)
        waiter = mock.Mock(side_effect=[
            TimeoutError("PLC remained Standby"),
            {"plc_status_code": 5},
        ])
        result = self.call_start(starter, waiter)
        self.assertEqual(result["plc_status_code"], 5)
        self.assertEqual(starter.call_count, 2)
        self.assertEqual(waiter.call_count, 2)

    def test_return_code_zero_but_standby_twice_is_immediate_error(self):
        starter = mock.Mock(return_value=None)
        waiter = mock.Mock(side_effect=TimeoutError("PLC remained Standby"))
        with self.assertRaisesRegex(
            thermal_runner.ThermalStartError,
            "failed to start after 2 complete attempts",
        ):
            self.call_start(starter, waiter)
        self.assertEqual(starter.call_count, 2)
        self.assertEqual(waiter.call_count, 2)
        for call in waiter.call_args_list:
            self.assertEqual(call.kwargs["timeout_seconds"], 60)


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

    def test_retry_reconnect_succeeds(self):
        first_client = mock.Mock()
        second_client = mock.Mock()
        clients = iter((first_client, second_client))
        snapshots = iter((RuntimeError("Snap7 TCP receive timeout"), {
            "plc_status_code": 5,
            "plc_status_text": "Cooling down",
        }))

        def read_snapshot(client, plc_cfg):
            result = next(snapshots)
            if isinstance(result, Exception):
                raise result
            return result

        reader = batch_runner.ReliablePLCSnapshotReader(
            {},
            max_attempts=3,
            retry_seconds=0,
            client_factory=lambda cfg: next(clients),
            snapshot_reader=read_snapshot,
            sleep_func=lambda seconds: None,
        )
        self.assertEqual(reader.read()["plc_status_code"], 5)
        first_client.disconnect.assert_called_once_with()

    def test_retry_exhaustion_is_clear(self):
        clients = [mock.Mock(), mock.Mock(), mock.Mock()]
        reader = batch_runner.ReliablePLCSnapshotReader(
            {},
            max_attempts=3,
            retry_seconds=0,
            client_factory=lambda cfg: clients.pop(0),
            snapshot_reader=mock.Mock(side_effect=RuntimeError("TCP receive timeout")),
            sleep_func=lambda seconds: None,
        )
        with self.assertRaisesRegex(
            batch_runner.PLCCommunicationError,
            "PLC communication failed after 3 attempts: TCP receive timeout",
        ):
            reader.read()

    def test_transition_state_survives_reconnect(self):
        first_client = mock.Mock()
        second_client = mock.Mock()
        clients = iter((first_client, second_client))
        snapshots = iter((RuntimeError("timeout"), {
            "plc_status_code": 4,
            "plc_status_text": "Countdown-Cooling Stage",
        }))

        def read_snapshot(client, plc_cfg):
            result = next(snapshots)
            if isinstance(result, Exception):
                raise result
            return result

        reader = batch_runner.ReliablePLCSnapshotReader(
            {}, retry_seconds=0,
            client_factory=lambda cfg: next(clients),
            snapshot_reader=read_snapshot,
            sleep_func=lambda seconds: None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_runner.wait_for_status_transition(
                name="test_transition",
                client=reader,
                plc_cfg={},
                seen_code=5,
                target_code=4,
                status_file=os.path.join(tmpdir, "status.json"),
                timeout_seconds=1,
                poll_seconds=0,
                seen_already=True,
            )
        self.assertEqual(result["plc_status_code"], 4)

    def test_stable_standby_survives_reconnect(self):
        clients = iter((mock.Mock(), mock.Mock()))
        snapshots = iter((
            {"plc_status_code": 1, "plc_status_text": "Standby"},
            RuntimeError("timeout"),
            {"plc_status_code": 1, "plc_status_text": "Standby"},
            {"plc_status_code": 1, "plc_status_text": "Standby"},
        ))

        def read_snapshot(client, plc_cfg):
            result = next(snapshots)
            if isinstance(result, Exception):
                raise result
            return result

        reader = batch_runner.ReliablePLCSnapshotReader(
            {}, retry_seconds=0,
            client_factory=lambda cfg: next(clients),
            snapshot_reader=read_snapshot,
            sleep_func=lambda seconds: None,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = batch_runner.wait_for_stable_status_code(
                name="test_standby",
                client=reader,
                plc_cfg={},
                expected_code=1,
                status_file=os.path.join(tmpdir, "status.json"),
                timeout_seconds=1,
                poll_seconds=0,
                consecutive_samples=3,
                activity_observed=True,
            )
        self.assertEqual(result["plc_status_code"], 1)


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

    def test_historical_stop_is_iv_only(self):
        original_status = app_task3.shared_state.server_status
        original_jobmode = app_task3.shared_state.jobmode
        app_task3.shared_state.server_status = "running"
        app_task3.shared_state.jobmode = "task3"
        flask_app = app_task3.Flask(__name__)
        try:
            with flask_app.test_request_context("/task3/stop", method="POST"), \
                    mock.patch.object(app_task3, "run_command", return_value=0) as run_command, \
                    mock.patch.object(app_task3, "build_plc_stop_command") as plc_stop, \
                    mock.patch.object(app_task3.os, "system", return_value=0):
                response = app_task3.Stop()
            self.assertEqual(response, ("", 204))
            self.assertEqual(app_task3.shared_state.server_status, "stopped")
            self.assertEqual(run_command.call_count, 1)
            self.assertIn("makefile_task3 stop", run_command.call_args.args[0])
            plc_stop.assert_not_called()
        finally:
            app_task3.shared_state.server_status = original_status
            app_task3.shared_state.jobmode = original_jobmode

    def test_thermal_stop_is_available_after_runner_error(self):
        original_status = app_task3.shared_state.server_status
        original_jobmode = app_task3.shared_state.jobmode
        app_task3.shared_state.server_status = "error"
        app_task3.shared_state.jobmode = "task3"
        flask_app = app_task3.Flask(__name__)
        try:
            failed_status = {
                "status": "error",
                "phase": "thermal_cycle",
                "thermal_stop_available": True,
            }
            with flask_app.test_request_context("/task3/thermal_stop", method="POST"), \
                    mock.patch.object(app_task3, "read_status", return_value=failed_status), \
                    mock.patch.object(app_task3, "run_command", return_value=0) as run_command, \
                    mock.patch.object(app_task3, "update_status") as update_status:
                response = app_task3.ThermalStop()
            self.assertEqual(response, ("", 204))
            self.assertEqual(app_task3.shared_state.server_status, "stopped")
            self.assertEqual(run_command.call_count, 1)
            self.assertIn("control_hmi.py", run_command.call_args.args[0])
            self.assertIn("--stop", run_command.call_args.args[0])
            self.assertFalse(update_status.call_args.args[0]["thermal_stop_available"])
        finally:
            app_task3.shared_state.server_status = original_status
            app_task3.shared_state.jobmode = original_jobmode

    def test_legacy_thermal_error_maps_only_to_new_thermal_stop(self):
        self.assertTrue(app_task3.thermal_stop_is_available({
            "runner": "run_selected_iv2_thermal_cycles.py",
            "status": "error",
            "plc_stop_possible": True,
        }))
        self.assertTrue(app_task3.thermal_stop_is_available({
            "runner": "run_selected_iv2_thermal_cycles.py",
            "status": "error",
            "last_command": "python control_hmi.py -c runtime.yml -f",
            "plc": {"plc_status_code": 5},
        }))
        self.assertFalse(app_task3.thermal_stop_is_available({
            "runner": "standalone_iv.py",
            "status": "error",
            "plc_stop_possible": True,
        }))
        self.assertFalse(app_task3.thermal_stop_is_available({
            "runner": "run_full_mmts_batch.py",
            "status": "error",
            "phase": "iv1",
            "last_command": "make -f makefile_task3 run",
        }))

    def test_runner_failure_does_not_build_plc_stop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            status_path = os.path.join(tmpdir, "status.json")
            from PythonTools.batch_status import write_status, read_status
            write_status({
                "status": "error",
                "phase": "thermal_cycle_1_ready_for_iv2",
                "phase_state": "error",
                "error_message": "PLC communication failed after 3 attempts: timeout",
            }, path=status_path)
            with mock.patch.object(app_task3, "build_plc_stop_command") as plc_stop:
                app_task3.record_thermal_cycle_failure(status_path, 1)
            plc_stop.assert_not_called()
            self.assertIn(
                "PLC communication failed after 3 attempts",
                read_status(path=status_path)["error_message"],
            )
            self.assertFalse(read_status(path=status_path)["thermal_stop_available"])

    def test_auto_destroy_preserves_error_without_plc_stop(self):
        original_status = app_task3.shared_state.server_status
        app_task3.shared_state.server_status = "error"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                status_path = os.path.join(tmpdir, "status.json")
                from PythonTools.batch_status import write_status, read_status
                reason = "PLC communication failed after 3 attempts: timeout"
                write_status({
                    "status": "error",
                    "phase": "cycle1_ready_for_iv2",
                    "phase_state": "error",
                    "error_message": reason,
                    "thermal_stop_available": True,
                }, path=status_path)
                with mock.patch.object(app_task3, "run_command", return_value=0), \
                        mock.patch.object(app_task3, "build_plc_stop_command") as plc_stop:
                    result = app_task3.auto_destroy_after_failure(
                        status_path, "cycle1_ready_for_iv2", reason
                    )
                self.assertEqual(result, 0)
                plc_stop.assert_not_called()
                final_status = read_status(path=status_path)
                self.assertEqual(final_status["error_message"], reason)
                self.assertTrue(final_status["thermal_stop_available"])
        finally:
            app_task3.shared_state.server_status = original_status


class IVWorkflowTests(unittest.TestCase):
    def test_standalone_iv1_uses_template_parameters_and_no_plc_command(self):
        conf = {key: "" for key in app_task3.CONF_DICT}
        conf["moduleID1L"] = "MODULE-1"
        with mock.patch.object(app_task3, "new_batch_id", return_value="20260813-120000"), \
                mock.patch.object(app_task3, "build_plc_stop_command") as plc_stop:
            command = app_task3.build_batch_iv_command("iv1", conf)
        self.assertIn("iteration=iteration_1", command)
        self.assertIn("currentTEMPERATURE=23", command)
        self.assertIn("currentHUMIDITY=50", command)
        self.assertIn("maxVOLTAGE=500", command)
        self.assertIn("batch=20260813-120000", command)
        self.assertNotIn("control_hmi.py", command)
        plc_stop.assert_not_called()

    def test_standalone_iv3_parameters_remain_unchanged(self):
        conf = {key: "" for key in app_task3.CONF_DICT}
        conf["moduleID1L"] = "MODULE-1"
        with mock.patch.object(app_task3, "new_batch_id", return_value="20260813-120001"):
            command = app_task3.build_batch_iv_command("iv3", conf)
        self.assertIn("iteration=iteration_4", command)
        self.assertIn("currentTEMPERATURE=20", command)
        self.assertIn("currentHUMIDITY=0", command)
        self.assertIn("maxVOLTAGE=850", command)
        self.assertIn("batch=20260813-120001", command)


class WorkflowOrderingTests(unittest.TestCase):
    def test_manual_thermal_segment_order_and_final_iv3(self):
        events = []
        cfg = {
            "batch": "BATCH",
            "total_cycles": 20,
            "iv2_cycles": [10],
            "normal_cold_hold_minutes": 10,
            "iv2_cold_hold_minutes": 59,
            "base_cycle_config": os.path.join(PLC_ROOT, "HMI_Control_single_cycle.yml"),
            "dewpoint_max_C": -30,
            "module_ids": {position: ("M1" if position == "1L" else "") for position in thermal_runner.IV_POSITIONS},
            "iv1_scan": {"iteration": "iteration_1", "temperature": 23, "humidity": 50, "max_voltage": 500},
            "iv2_scan": {"iteration": "iteration_2", "temperature": -40, "humidity": 0, "max_voltage": 850},
            "iv3_scan": {"iteration": "iteration_4", "temperature": 20, "humidity": 0, "max_voltage": 850},
        }
        args = mock.Mock(
            config="unused.yml", status_file="unused.json", poll_seconds=0,
            start_validation_timeout_seconds=60, transition_timeout_minutes=1,
        )
        client = mock.Mock()
        client.read.return_value = {"plc_status_code": 1}
        segment_configs = []
        standby_calls = []

        def record_iv(name, *unused_args):
            events.append(name)

        def record_segment_start(**kwargs):
            events.append(f"START {kwargs['name']}")
            return {"plc_status_code": 5}

        def record_segment_config(base_path, output_path, cycles, cold_hold):
            segment_configs.append((cycles, cold_hold))

        def record_standby(**kwargs):
            standby_calls.append(kwargs)
            events.append("Standby")

        with mock.patch.object(thermal_runner, "parse_args", return_value=args), \
                mock.patch.object(thermal_runner, "load_workflow_config", return_value=cfg), \
                mock.patch.object(batch_runner, "ReliablePLCSnapshotReader", return_value=client), \
                mock.patch.object(batch_runner, "run_iv_scan", side_effect=record_iv), \
                mock.patch.object(batch_runner, "wait_for_dewpoint", side_effect=lambda **kwargs: events.append("dewpoint")), \
                mock.patch.object(batch_runner, "wait_for_status_transition", side_effect=lambda **kwargs: events.append("5->4")), \
                mock.patch.object(batch_runner, "wait_for_stable_status_code", side_effect=record_standby), \
                mock.patch.object(thermal_runner, "start_thermal_segment_with_validation", side_effect=record_segment_start), \
                mock.patch.object(thermal_runner, "write_segment_config", side_effect=record_segment_config), \
                mock.patch.object(thermal_runner, "write_status"), \
                mock.patch.object(thermal_runner, "update_status"), \
                mock.patch("plc_io.load_config", return_value={"plc": {}}):
            thermal_runner.main()
        self.assertEqual(events, [
            "iv1",
            "dewpoint",
            "START thermal_segment_1",
            "Standby",
            "START thermal_segment_2",
            "5->4",
            "iv2",
            "Standby",
            "START thermal_segment_3",
            "Standby",
            "iv3",
        ])
        self.assertEqual(segment_configs, [(9, 10), (1, 59), (10, 10)])
        self.assertEqual(
            [call["timeout_seconds"] for call in standby_calls],
            [9 * 60, 1 * 60, 10 * 60],
        )

    def test_final_iv3_failure_does_not_mark_thermal_program_active(self):
        cfg = {
            "batch": "BATCH",
            "total_cycles": 1,
            "iv2_cycles": [],
            "normal_cold_hold_minutes": 10,
            "iv2_cold_hold_minutes": 59,
            "base_cycle_config": os.path.join(PLC_ROOT, "HMI_Control_single_cycle.yml"),
            "dewpoint_max_C": -30,
            "module_ids": {position: ("M1" if position == "1L" else "") for position in thermal_runner.IV_POSITIONS},
            "iv1_scan": {"iteration": "iteration_1", "temperature": 23, "humidity": 50, "max_voltage": 500},
            "iv2_scan": {"iteration": "iteration_2", "temperature": -40, "humidity": 0, "max_voltage": 850},
            "iv3_scan": {"iteration": "iteration_4", "temperature": 20, "humidity": 0, "max_voltage": 850},
        }
        args = mock.Mock(
            config="unused.yml", status_file="unused.json", poll_seconds=0,
            start_validation_timeout_seconds=60, transition_timeout_minutes=1,
        )
        client = mock.Mock()
        client.read.return_value = {"plc_status_code": 1}
        updates = []

        def run_iv(name, *unused_args):
            if name == "iv3":
                raise RuntimeError("final IV3 failed")

        with mock.patch.object(thermal_runner, "parse_args", return_value=args), \
                mock.patch.object(thermal_runner, "load_workflow_config", return_value=cfg), \
                mock.patch.object(batch_runner, "ReliablePLCSnapshotReader", return_value=client), \
                mock.patch.object(batch_runner, "run_iv_scan", side_effect=run_iv), \
                mock.patch.object(batch_runner, "wait_for_dewpoint"), \
                mock.patch.object(batch_runner, "wait_for_stable_status_code"), \
                mock.patch.object(thermal_runner, "start_thermal_segment_with_validation", return_value={"plc_status_code": 5}), \
                mock.patch.object(thermal_runner, "write_segment_config"), \
                mock.patch.object(thermal_runner, "write_status"), \
                mock.patch.object(thermal_runner, "update_status", side_effect=lambda payload, **kwargs: updates.append(payload)), \
                mock.patch("plc_io.load_config", return_value={"plc": {}}):
            with self.assertRaisesRegex(RuntimeError, "final IV3 failed"):
                thermal_runner.main()

        self.assertEqual(updates[-1]["status"], "error")
        self.assertFalse(updates[-1]["thermal_stop_available"])
        self.assertIn("final IV3 failed", updates[-1]["error_message"])

    def test_autotest_sequence_and_scan_values_remain_unchanged(self):
        with open(os.path.join(UI_ROOT, "data", "full_batch_config.example.yml"), "r", encoding="utf-8") as fin:
            cfg = yaml.safe_load(fin)
        self.assertEqual(cfg["cycle_configs"], {
            "first_cycle": "HMI_Control.yml",
            "remaining_cycles": "HMI_Control_5cycle.yml",
        })
        self.assertEqual(cfg["iv_scans"], {
            "iv1": {"iteration": "iteration_1", "temperature": 23, "humidity": 50, "max_voltage": 500},
            "iv2": {"iteration": "iteration_2", "temperature": -40, "humidity": 0, "max_voltage": 850},
            "iv3": {"iteration": "iteration_4", "temperature": 20, "humidity": 0, "max_voltage": 850},
        })


if __name__ == "__main__":
    unittest.main()
