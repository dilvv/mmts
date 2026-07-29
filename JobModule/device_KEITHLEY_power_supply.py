import asyncio
import pyvisa
import sys
import os
import numpy as np
from datetime import datetime
import asyncio.exceptions

import time

# Import logging modules or create a simple alternative
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from PythonTools.MyLogging_BashJob1 import log as rs232log
    from PythonTools.MyLogging_BashJob1 import log as bashlog
except ImportError:
    # Simple logger if modules not found
    class SimpleLogger:
        def debug(self, msg): print(f"[DEBUG] {msg}")
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    rs232log = SimpleLogger()
    bashlog = SimpleLogger()

class RS232Dev:
    """RS232 device class for managing instrument connections"""
    def __init__(self, tag):
        self.rm = pyvisa.ResourceManager()
        self.tag = tag
        self.task = None
        self.instrument = None

    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'instrument') and self.instrument is not None:
            self.instrument.close()
        if hasattr(self, 'rm') and self.rm is not None:
            self.rm.close()

    def set_task(self, t):
        """Set an async task"""
        self.task = t

    async def await_task(self):
        """Wait for task completion"""
        if not hasattr(self, 'task') or self.task is None:
            return  # No task to wait for

        if not self.task.done():
            bashlog.debug(f'[{self.tag} - Await] Waiting for measurement task to complete')
            await self.task


class KeithleyCommands:
    """Keithley commands class with SCPI command constants"""
    # Reset and status commands
    RESET = "*RST"
    CLEAR = "*CLS"
    IDN = "*IDN?"
    OPC = "*OPC?"

    # Error query
    ERROR = ":SYSTem:ERRor?"

    # Source control commands
    SOURCE_VOLTAGE = ":SOURce:FUNCtion:MODE VOLTage"
    SOURCE_CURRENT = ":SOURce:FUNCtion:MODE CURRent"

    # Measurement commands
    MEASURE_VOLTAGE = ":SENSe:FUNCtion 'VOLTage:DC'"
    MEASURE_CURRENT = ":SENSe:FUNCtion 'CURRent:DC'"
    MEASURE_RESISTANCE = ":SENSe:FUNCtion 'RESistance'"
    MEASURE_CONCURRENT_ON = ":SENSe:FUNCtion:CONCurrent ON"
    MEASURE_CONCURRENT_OFF = ":SENSe:FUNCtion:CONCurrent OFF"

    # Sweep commands
    SWEEP_LINEAR = ":SOURce:SWEep:SPACing LINear"
    SWEEP_LOG = ":SOURce:SWEep:SPACing LOGarithmic"

    # Output control
    OUTPUT_ON = ":OUTPut:STATe ON"
    OUTPUT_OFF = ":OUTPut:STATe OFF"

    # Trigger commands
    TRIGGER_IMMEDIATE = ":INITiate"
    TRIGGER_ABORT = ":ABORt"

    # Data reading commands
    READ = ":READ?"
    FETCH = ":FETCh?"
    MEASURE = ":MEASure?"


class KeithleyInstrument:
    """Keithley instrument control class"""
    def __init__(self, device_tag, resource_name):
        """Initialize Keithley instrument

        Args:
            device_tag: Device tag for logging
            resource_name: VISA resource name, e.g., "GPIB0::24::INSTR"
        """
        self.device_tag = device_tag
        self.resource_name = resource_name
        self.rs232_dev = None
        self.instrument = None

    async def connect(self):
        """Connect to the instrument and perform basic setup"""
        try:
            self.rs232_dev = RS232Dev(self.device_tag)
            instr = self.rs232_dev.rm.open_resource(self.resource_name)

            # Set communication parameters
            if self.resource_name.startswith("ASRL"):
                instr.baud_rate = 9600
                instr.data_bits = 8
                instr.stop_bits = pyvisa.constants.StopBits.one
                instr.parity = pyvisa.constants.Parity.none
                instr.flow_control = pyvisa.constants.VI_ASRL_FLOW_NONE

            instr.timeout = 10000  # 10 second timeout, may be needed for sweep operations

            # Store instrument instance
            self.rs232_dev.instrument = instr
            self.instrument = instr

            # Clear error queue and set up instrument
            await self.send_command(KeithleyCommands.CLEAR)

            # Verify connection
            idn = await self.query_command(KeithleyCommands.IDN)
            if idn:
                bashlog.info(f"Connected to instrument: {idn}")
                return True
            else:
                bashlog.error("Unable to get instrument identification")
                return False

        except Exception as e:
            bashlog.error(f"Error connecting to {self.resource_name}: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the instrument"""
        try:
            if self.instrument:
                # Ensure output is off
                await self.output_off()

                # Close connection
                self.instrument.close()
                self.instrument = None

            if self.rs232_dev:
                if hasattr(self.rs232_dev, 'rm'):
                    self.rs232_dev.rm.close()
                self.rs232_dev = None

            bashlog.info(f"Disconnected from {self.resource_name}")
            return True
        except Exception as e:
            bashlog.error(f"Error disconnecting: {e}")
            return False

    async def send_command(self, command):
        """Send command to the instrument

        Args:
            command: SCPI command string or list of commands

        Returns:
            bool: True on success, False on failure
        """
        if not self.instrument:
            bashlog.error("Instrument not connected")
            return False

        try:
            commands = command if isinstance(command, list) else [command]
            for cmd in commands:
                # bashlog.info(f"[DEBUG-verbose] {cmd}")
                self.instrument.write(cmd)
                await asyncio.sleep(0.05)  # Small delay to ensure command processing
            return True
        except Exception as e:
            bashlog.error(f"Error sending command: {e}")
            return False

    async def query_command(self, command):
        """Send query command to the instrument and get response

        Args:
            command: SCPI query command

        Returns:
            str: Command response, None on failure
        """
        if not self.instrument:
            bashlog.error("Instrument not connected")
            return None

        try:
            result = self.instrument.query(command)
            return result.strip() if result else None
        except Exception as e:
            bashlog.error(f"Error querying command: {e}")
            return None

    async def check_errors(self):
        """Check instrument error queue and log all errors

        Returns:
            list: List of error messages, empty list if no errors
        """
        errors = []
        if not self.instrument:
            return errors

        try:
            while True:
                error = await self.query_command(KeithleyCommands.ERROR)
                if not error or "0,\"No error\"" in error:
                    break
                errors.append(error)
                bashlog.error(f"Instrument error: {error}")

            return errors
        except Exception as e:
            bashlog.error(f"Error checking errors: {e}")
            return [f"Error checking errors: {e}"]

    async def reset(self):
        """Reset instrument to default state and clear error queue"""
        result = await self.send_command([KeithleyCommands.RESET, KeithleyCommands.CLEAR])
        await self.check_errors()
        return result

    async def setup_as_voltage_source(self, voltage_range=20, voltage_level=0, current_compliance=0.1):
        """Configure instrument as voltage source

        Args:
            voltage_range: Voltage range in volts
            voltage_level: Initial voltage value in volts
            current_compliance: Current limit in amps

        Returns:
            bool: True on success, False on failure
        """
        cmds = [
            KeithleyCommands.RESET,
            KeithleyCommands.SOURCE_VOLTAGE,
            f":SOURce:VOLTage:RANGe {voltage_range}",
            f":SOURce:VOLTage:LEVel {voltage_level}",
            KeithleyCommands.MEASURE_CURRENT,
            f":SENSe:CURRent:PROTection {current_compliance}",
            ":SENSe:CURRent:RANGe:AUTO ON",
            # Set integration time (NPLC - Number of Power Line Cycles)
            ":SENSe:CURRent:NPLCycles 1.0",
            # Set data format
            ":FORMat:ELEMents VOLTage,CURRent,RESistance,TIME,STATus"
        ]

        result = await self.send_command(cmds)
        await self.check_errors()

        if result:
            bashlog.info(f"Configured as voltage source, range {voltage_range}V, initial value {voltage_level}V, current limit {current_compliance}A")

        return result

    async def setup_as_current_source(self, current_range=0.1, current_level=0, voltage_compliance=20):
        """Configure instrument as current source

        Args:
            current_range: Current range in amps
            current_level: Initial current value in amps
            voltage_compliance: Voltage limit in volts

        Returns:
            bool: True on success, False on failure
        """
        cmds = [
            KeithleyCommands.RESET,
            KeithleyCommands.SOURCE_CURRENT,
            f":SOURce:CURRent:RANGe {current_range}",
            f":SOURce:CURRent:LEVel {current_level}",
            KeithleyCommands.MEASURE_VOLTAGE,
            f":SENSe:VOLTage:PROTection {voltage_compliance}",
            ":SENSe:VOLTage:RANGe:AUTO ON",
            # Set integration time
            ":SENSe:VOLTage:NPLCycles 1.0",
            # Set data format
            ":FORMat:ELEMents VOLTage,CURRent,RESistance,TIME,STATus"
        ]

        result = await self.send_command(cmds)
        await self.check_errors()

        if result:
            bashlog.info(f"Configured as current source, range {current_range}A, initial value {current_level}A, voltage limit {voltage_compliance}V")

        return result

    async def setup_measurement_speed(self, nplc=1.0):
        """Set measurement speed/integration time

        Args:
            nplc: Number of power line cycles (0.01 to 10), smaller values are faster but noisier

        Returns:
            bool: True on success, False on failure
        """
        cmds = [
            f":SENSe:CURRent:NPLCycles {nplc}",
            f":SENSe:VOLTage:NPLCycles {nplc}",
            f":SENSe:RESistance:NPLCycles {nplc}"
        ]

        result = await self.send_command(cmds)
        await self.check_errors()

        if result:
            bashlog.info(f"Measurement speed set to {nplc} NPLC")

        return result

    async def setup_measurement_filter(self, enable=True, count=10, type="REPeat"):
        """Set measurement filter

        Args:
            enable: Whether to enable the filter
            count: Filter count (1 to 100)
            type: Filter type, "REPeat" or "MOVing"

        Returns:
            bool: True on success, False on failure
        """
        state = "ON" if enable else "OFF"
        cmds = [
            f":SENSe:AVERage:TCONtrol {type}",
            f":SENSe:AVERage:COUNt {count}",
            f":SENSe:AVERage:STATe {state}"
        ]

        result = await self.send_command(cmds)
        await self.check_errors()

        if result:
            status = "enabled" if enable else "disabled"
            bashlog.info(f"Measurement filter {status}, count {count}, type {type}")

        return result

    async def setup_auto_zero(self, state="ON"):
        """Set auto-zero function

        Args:
            state: Auto-zero state, "ON", "OFF", or "ONCE"
                  ON - Enable auto-zero
                  OFF - Disable auto-zero
                  ONCE - Perform one auto-zero operation then disable

        Returns:
            bool: True on success, False on failure
        """
        if state not in ["ON", "OFF", "ONCE"]:
            bashlog.error(f"Invalid auto-zero state: {state}")
            return False

        cmd = f":SYSTem:AZERo:STATe {state}"
        result = await self.send_command(cmd)
        await self.check_errors()

        if result:
            if state == "ONCE":
                bashlog.info("Performed one auto-zero operation")
            else:
                status = "enabled" if state == "ON" else "disabled"
                bashlog.info(f"Auto-zero {status}")

        return result

    async def setup_sense_range_sync(self, enable=True):
        """Set measurement range and compliance range synchronization

        When enabled, measurement range automatically follows compliance range settings.
        For example: If current compliance is set to 10mA, current measurement range will also be set to 10mA range.

        Args:
            enable: Whether to enable synchronization

        Returns:
            bool: True on success, False on failure
        """
        state = "ON" if enable else "OFF"
        # Set sync for both current and voltage
        cmds = [
            f":SENSe:CURRent:PROTection:RSYNchronize {state}",
            f":SENSe:VOLTage:PROTection:RSYNchronize {state}"
        ]

        result = await self.send_command(cmds)
        await self.check_errors()

        if result:
            status = "enabled" if enable else "disabled"
            bashlog.info(f"Measurement range and compliance range synchronization {status}")

        return result

    async def set_output_off_mode(self, mode="NORMal"):
        """Set output off mode

        Args:
            mode: Output off mode
                 NORMal - Normal mode
                 ZERO - Zero output mode
                 HIMPedance - High impedance mode
                 GUARd - Guard mode

        Returns:
            bool: True on success, False on failure
        """
        if mode not in ["NORMal", "ZERO", "HIMPedance", "GUARd"]:
            bashlog.error(f"Invalid output off mode: {mode}")
            return False

        cmd = f":OUTPut:SMODe {mode}"
        result = await self.send_command(cmd)
        await self.check_errors()

        if result:
            bashlog.info(f"Output off mode set to {mode}")

        return result

    async def set_data_format(self, elements=None, format_type="ASCii"):
        """Set data format

        Args:
            elements: List of data elements to include, e.g., ["VOLTage", "CURRent", "RESistance", "TIME", "STATus"]
                     If None, all elements will be included
            format_type: Data format type, "ASCii", "REAL", or "SREal"

        Returns:
            bool: True on success, False on failure
        """
        cmds = []

        # Set data format type
        cmds.append(f":FORMat:DATA {format_type}")

        # Set data elements
        if elements is not None:
            elements_str = ",".join(elements)
            cmds.append(f":FORMat:ELEMents {elements_str}")
        else:
            # Default to include all elements
            cmds.append(":FORMat:ELEMents VOLTage,CURRent,RESistance,TIME,STATus")

        result = await self.send_command(cmds)
        await self.check_errors()

        if result:
            if elements is not None:
                bashlog.info(f"Data format set to {format_type}, including elements: {elements}")
            else:
                bashlog.info(f"Data format set to {format_type}, including all elements")

        return result

    async def check_compliance_state(self):
        """Check if source is in compliance state

        Returns:
            tuple: (voltage compliance state, current compliance state), True indicates in compliance
        """
        try:
            # Check current compliance state for voltage source
            current_compliance = await self.query_command(":SENSe:CURRent:PROTection:TRIPped?")
            # Check voltage compliance state for current source
            voltage_compliance = await self.query_command(":SENSe:VOLTage:PROTection:TRIPped?")

            current_tripped = current_compliance == "1"
            voltage_tripped = voltage_compliance == "1"

            if current_tripped:
                bashlog.warning("Current compliance state triggered")
            if voltage_tripped:
                bashlog.warning("Voltage compliance state triggered")

            return voltage_tripped, current_tripped
        except Exception as e:
            bashlog.error(f"Error checking compliance state: {e}")
            return False, False

    async def set_voltage(self, voltage_level):
        """Set output voltage

        Args:
            voltage_level: Voltage value in volts

        Returns:
            bool: True on success, False on failure
        """
        result = await self.send_command(f":SOURce:VOLTage:LEVel {voltage_level}")

        if result:
            bashlog.info(f"Voltage set to {voltage_level} V")

        return result

    async def set_current(self, current_level):
        """Set output current

        Args:
            current_level: Current value in amps

        Returns:
            bool: True on success, False on failure
        """
        result = await self.send_command(f":SOURce:CURRent:LEVel {current_level}")

        if result:
            bashlog.info(f"Current set to {current_level} A")

        return result

    async def output_on(self):
        """Turn output on"""
        result = await self.send_command(KeithleyCommands.OUTPUT_ON)

        if result:
            bashlog.info("Output turned on")

        return result

    async def output_off(self):
        """Turn output off"""
        result = await self.send_command(KeithleyCommands.OUTPUT_OFF)

        if result:
            bashlog.info("Output turned off")

        return result

    async def read_measurements(self):
        """Read current measurement values

        Returns:
            dict: Measurement results dict including voltage, current, etc.
        """
        try:
            response = await self.query_command(KeithleyCommands.READ)
            if not response:
                bashlog.error("Failed to read measurement, no response")
                return None

            values = response.split(',')
            if len(values) >= 4:  # voltage, current, resistance, time, status
                result = {
                    'voltage': float(values[0]),
                    'current': float(values[1]),
                    'timestamp': float(values[2]),
                    'status': int(float(values[3]))
                }
                return result
                # +1.000000E+00,-3.040113E-11,+8.155492E+03,+2.150800E+04
            else:
                bashlog.error(f"Failed to read measurement, incorrect data format: {response}")
                return None
        except Exception as e:
            bashlog.error(f"Error reading measurement: {e}")
            return None

    async def read_iv(self):
        """Read current voltage and current

        Returns:
            tuple: (voltage, current), returns (None, None) on failure
        """
        measurements = await self.read_measurements()

        if measurements:
            return measurements['voltage'], measurements['current']

        return None, None

    async def setup_voltage_sweep_linear(self, start_v, stop_v, step_v=None, points=None):
        """Set up linear voltage sweep

        Must specify either step_v or points

        Args:
            start_v: Start voltage
            stop_v: Stop voltage
            step_v: Voltage step
            points: Number of sweep points

        Returns:
            bool: True on success, False on failure
        """
        if step_v is None and points is None:
            bashlog.error("Must specify either voltage step or number of sweep points")
            return False

        if step_v is not None and points is not None:
            bashlog.error("Cannot specify both voltage step and number of sweep points")
            return False

        try:
            cmds = [
                KeithleyCommands.SOURCE_VOLTAGE,
                ":SOURce:VOLTage:MODE SWEep",
                KeithleyCommands.SWEEP_LINEAR,  # Linear sweep
                f":SOURce:VOLTage:STARt {start_v}",
                f":SOURce:VOLTage:STOP {stop_v}",
            ]

            if step_v is not None:
                cmds.append(f":SOURce:VOLTage:STEP {step_v}")
            else:  # points is not None
                cmds.append(f":SOURce:SWEep:POINts {points}")

            # Set sweep source range mode
            cmds.append(":SOURce:SWEep:RANGing BEST")  # Use best fixed range

            result = await self.send_command(cmds)
            await self.check_errors()

            if result:
                if step_v is not None:
                    bashlog.info(f"Linear voltage sweep setup: {start_v}V to {stop_v}V, step {step_v}V")
                else:
                    bashlog.info(f"Linear voltage sweep setup: {start_v}V to {stop_v}V, {points} points")

            return result
        except Exception as e:
            bashlog.error(f"Error setting up voltage sweep: {e}")
            return False

    async def setup_voltage_sweep_log(self, start_v, stop_v, points):
        """Set up logarithmic voltage sweep

        Args:
            start_v: Start voltage (must be non-zero and same sign as stop_v)
            stop_v: Stop voltage
            points: Number of sweep points

        Returns:
            bool: True on success, False on failure
        """
        if start_v * stop_v <= 0:
            bashlog.error("Start and stop voltages for logarithmic sweep must be non-zero and have the same sign")
            return False

        try:
            cmds = [
                KeithleyCommands.SOURCE_VOLTAGE,
                ":SOURce:VOLTage:MODE SWEep",
                KeithleyCommands.SWEEP_LOG,  # Logarithmic sweep
                f":SOURce:VOLTage:STARt {start_v}",
                f":SOURce:VOLTage:STOP {stop_v}",
                f":SOURce:SWEep:POINts {points}",
                ":SOURce:SWEep:RANGing BEST"  # Use best fixed range
            ]

            result = await self.send_command(cmds)
            await self.check_errors()

            if result:
                bashlog.info(f"Logarithmic voltage sweep setup: {start_v}V to {stop_v}V, {points} points")

            return result
        except Exception as e:
            bashlog.error(f"Error setting up logarithmic voltage sweep: {e}")
            return False

    async def setup_current_sweep_linear(self, start_i, stop_i, step_i=None, points=None):
        """Set up linear current sweep

        Must specify either step_i or points

        Args:
            start_i: Start current
            stop_i: Stop current
            step_i: Current step
            points: Number of sweep points

        Returns:
            bool: True on success, False on failure
        """
        if step_i is None and points is None:
            bashlog.error("Must specify either current step or number of sweep points")
            return False

        if step_i is not None and points is not None:
            bashlog.error("Cannot specify both current step and number of sweep points")
            return False

        try:
            cmds = [
                KeithleyCommands.SOURCE_CURRENT,
                ":SOURce:CURRent:MODE SWEep",
                KeithleyCommands.SWEEP_LINEAR,  # Linear sweep
                f":SOURce:CURRent:STARt {start_i}",
                f":SOURce:CURRent:STOP {stop_i}",
            ]

            if step_i is not None:
                cmds.append(f":SOURce:CURRent:STEP {step_i}")
            else:  # points is not None
                cmds.append(f":SOURce:SWEep:POINts {points}")

            # Set sweep source range mode
            cmds.append(":SOURce:SWEep:RANGing BEST")  # Use best fixed range

            result = await self.send_command(cmds)
            await self.check_errors()

            if result:
                if step_i is not None:
                    bashlog.info(f"Linear current sweep setup: {start_i}A to {stop_i}A, step {step_i}A")
                else:
                    bashlog.info(f"Linear current sweep setup: {start_i}A to {stop_i}A, {points} points")

            return result
        except Exception as e:
            bashlog.error(f"Error setting up current sweep: {e}")
            return False

    async def setup_buffer(self, buffer_size=100):
        """Set up data buffer

        Args:
            buffer_size: Buffer size (1 to 2500)

        Returns:
            bool: True on success, False on failure
        """

        try:
            # Stop data feed if active
            await self.send_command(":TRACe:FEED:CONTrol NEVER")

            # Clear the buffer
            await self.send_command(":TRACe:CLEar")

            # Set buffer size
            await self.send_command(f":TRACe:POINts {buffer_size}")

            # Re-enable data feed
            cmds = [
                ":TRACe:FEED SENSe",
                ":TRACe:FEED:CONTrol NEXT"
            ]
            result = await self.send_command(cmds)

            await self.check_errors()

            if result:
                bashlog.info(f"Data buffer setup for {buffer_size} points")

            return result

        except Exception as e:
            bashlog.error(f"Error setting up data buffer: {e}")
            return False

    async def read_buffer(self):
        """Read data from buffer

        Returns:
            list: List of measurement results in buffer
        """
        try:
            response = await self.query_command(":TRACe:DATA?")
            if not response:
                bashlog.error("Failed to read buffer, no response")
                return []

            # Process buffer data
            values = response.split(',')
            points = len(values) // 5  # Each measurement point has 5 values
            results = []

            for i in range(points):
                point = {
                    'voltage': float(values[i*5]),
                    'current': float(values[i*5+1]),
                    'resistance': float(values[i*5+2]),
                    'timestamp': float(values[i*5+3]),
                    'status': int(float(values[i*5+4]))
                }
                results.append(point)

            return results
        except Exception as e:
            bashlog.error(f"Error reading buffer data: {e}")
            return []

    async def perform_iv_sweep(self, start_v, stop_v, points=None, step_v=None, use_buffer=True):
        """Perform IV sweep

        Args:
            start_v: Start voltage
            stop_v: Stop voltage
            points: Number of sweep points
            step_v: Voltage step
            use_buffer: Whether to use buffer to store data

        Returns:
            list: List of measurement results, empty list on failure
        """
        try:
            # Set up as voltage source and configure sweep
            await self.setup_as_voltage_source()

            # Set up sweep
            if step_v is not None:
                sweep_result = await self.setup_voltage_sweep_linear(start_v, stop_v, step_v=step_v)
                # Calculate required points
                total_points = int(abs(stop_v - start_v) / step_v) + 1
            elif points is not None:
                sweep_result = await self.setup_voltage_sweep_linear(start_v, stop_v, points=points)
                total_points = points
            else:
                # Default to 10 points
                points = 10
                sweep_result = await self.setup_voltage_sweep_linear(start_v, stop_v, points=points)
                total_points = points

            if not sweep_result:
                bashlog.error("Failed to set up sweep")
                return []

            # Set trigger count
            await self.send_command(f":TRIGger:COUNt {total_points}")

            if use_buffer:
                # Set up data buffer
                await self.setup_buffer(total_points)

            # Turn on output and run sweep
            await self.output_on()
            await self.send_command(KeithleyCommands.TRIGGER_IMMEDIATE)

            # Wait for sweep to complete
            await self.query_command(KeithleyCommands.OPC)

            results = []
            if use_buffer:
                # Read data from buffer
                buffer_data = await self.read_buffer()
                for point in buffer_data:
                    results.append((point['voltage'], point['current']))
            else:
                # Use FETCh? command to read data
                fetch_data = await self.query_command(KeithleyCommands.FETCH)
                if fetch_data:
                    values = fetch_data.split(',')
                    num_points = len(values) // 5
                    for i in range(num_points):
                        voltage = float(values[i*5])
                        current = float(values[i*5+1])
                        results.append((voltage, current))

            # Turn off output
            await self.output_off()

            # Save results to file
            if results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"iv_sweep_{timestamp}.csv"
                with open(filename, 'w') as f:
                    f.write("Voltage(V),Current(A)\n")
                    for v, i in results:
                        f.write(f"{v},{i}\n")
                bashlog.info(f"IV sweep completed, results saved to {filename}")

            return results
        except Exception as e:
            bashlog.error(f"Error performing IV sweep: {e}")
            # Ensure output is off
            await self.output_off()
            return []

    async def start_iv_monitor(self, interval=2.0, save_data=True, max_samples=1000):
        """Start background IV monitoring task

        Args:
            interval: Measurement interval in seconds
            save_data: Whether to save data to file
            max_samples: Maximum number of samples to keep, older samples will be discarded

        Returns:
            bool: True on success, False on failure
        """
        if not self.rs232_dev:
            bashlog.error("Instrument not connected")
            return False

        try:
            # Create data storage
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"iv_monitor_{timestamp}.csv"

            # Create monitoring task
            async def monitor_task():
                try:
                    bashlog.info("IV monitoring started")

                    # Create data storage
                    data_buffer = []

                    # If saving data, create and write CSV header
                    if save_data:
                        with open(filename, 'w') as f:
                            f.write("Timestamp,Voltage(V),Current(A),Status\n")

                    counter = 0
                    while True:
                        # Read measurements
                        measurements = await self.read_measurements()
                        if measurements:
                            voltage = measurements['voltage']
                            current = measurements['current']
                            status = measurements['status']
                            timestamp = datetime.now().isoformat()

                            # Check compliance state
                            v_tripped, i_tripped = await self.check_compliance_state()
                            compliance_info = ""
                            if v_tripped:
                                compliance_info = " (Voltage compliance triggered)"
                            if i_tripped:
                                compliance_info = " (Current compliance triggered)"

                            # Display information
                            bashlog.info(f"IV monitor: V={voltage}V, I={current}A{compliance_info}")

                            # Store data
                            data_point = {
                                'timestamp': timestamp,
                                'voltage': voltage,
                                'current': current,
                                'status': status
                            }

                            # Add to buffer
                            data_buffer.append(data_point)
                            if len(data_buffer) > max_samples:
                                data_buffer.pop(0)  # Remove oldest data point

                            # Save to file if needed
                            if save_data:
                                with open(filename, 'a') as f:
                                    f.write(f"{timestamp},{voltage},{current},{status}\n")

                            counter += 1
                            if counter % 10 == 0:  # Show storage info every 10 data points
                                if save_data:
                                    bashlog.info(f"Stored {counter} data points to {filename}")

                        await asyncio.sleep(interval)

                except asyncio.CancelledError:
                    bashlog.info("IV monitoring stopped")
                    # Store final data
                    self.monitor_data = data_buffer
                    if save_data:
                        bashlog.info(f"All monitoring data saved to {filename}")
                    return data_buffer

                except Exception as e:
                    bashlog.error(f"Error during IV monitoring: {e}")
                    # Store final data
                    self.monitor_data = data_buffer
                    return data_buffer

            # Start task and store in device object
            task = asyncio.create_task(monitor_task())
            self.rs232_dev.set_task(task)
            # Store filename for later reference
            self.monitor_filename = filename if save_data else None
            return True

        except Exception as e:
            bashlog.error(f"Error starting IV monitoring: {e}")
            return False

    async def stop_iv_monitor(self):
        """Stop IV monitoring task

        Returns:
            tuple: (success status, collected data), returns (False, None) on failure
        """
        if not self.rs232_dev:
            return False, None

        try:
            data = None
            if hasattr(self.rs232_dev, 'task') and self.rs232_dev.task:
                # Cancel task
                self.rs232_dev.task.cancel()
                try:
                    # Wait for task to cancel and get results
                    await asyncio.sleep(0.5)
                    # Check if monitoring data exists
                    if hasattr(self, 'monitor_data'):
                        data = self.monitor_data
                except asyncio.CancelledError:
                    pass

                bashlog.info("IV monitoring stopped")

                # Show data storage location
                if hasattr(self, 'monitor_filename') and self.monitor_filename:
                    bashlog.info(f"Complete monitoring data saved to {self.monitor_filename}")

            return True, data
        except Exception as e:
            bashlog.error(f"Error stopping IV monitoring: {e}")
            return False, None

    async def read_status_registers(self):
        """Read instrument status registers

        Returns:
            dict: Instrument status information
        """
        try:
            # Read various status registers
            measurement_status = await self.query_command(":STATus:MEASurement:CONDition?")
            operation_status = await self.query_command(":STATus:OPERation:CONDition?")
            questionable_status = await self.query_command(":STATus:QUEStionable:CONDition?")

            # Read standard event register
            event_status = await self.query_command("*ESR?")

            # Parse to integers
            meas_status = int(measurement_status) if measurement_status else 0
            op_status = int(operation_status) if operation_status else 0
            quest_status = int(questionable_status) if questionable_status else 0
            event_status = int(event_status) if event_status else 0

            # Parse measurement status register meanings
            meas_status_info = {}
            if meas_status & 0x1:    meas_status_info["LIMIT1_FAIL"] = True
            if meas_status & 0x2:    meas_status_info["LIMIT2_LOW_FAIL"] = True
            if meas_status & 0x4:    meas_status_info["LIMIT2_HIGH_FAIL"] = True
            if meas_status & 0x8:    meas_status_info["LIMIT3_LOW_FAIL"] = True
            if meas_status & 0x10:   meas_status_info["LIMIT3_HIGH_FAIL"] = True
            if meas_status & 0x20:   meas_status_info["LIMIT4_FAIL"] = True
            if meas_status & 0x40:   meas_status_info["READING_OVERFLOW"] = True
            if meas_status & 0x80:   meas_status_info["BUFFER_FULL"] = True
            if meas_status & 0x100:  meas_status_info["BUFFER_HALF_FULL"] = True
            if meas_status & 0x200:  meas_status_info["READING_AVAILABLE"] = True

            # Parse operation status register meanings
            op_status_info = {}
            if op_status & 0x1:    op_status_info["CALIBRATING"] = True
            if op_status & 0x2:    op_status_info["SETTLING"] = True
            if op_status & 0x4:    op_status_info["TRIGGER_LAYER"] = True
            if op_status & 0x8:    op_status_info["ARM_LAYER"] = True
            if op_status & 0x10:   op_status_info["MEASURING"] = True
            if op_status & 0x200:  op_status_info["TRIGGER_SWEEPING"] = True
            if op_status & 0x800:  op_status_info["IDLE"] = True

            # Parse questionable status register meanings
            quest_status_info = {}
            if quest_status & 0x1:    quest_status_info["VOLTAGE_SUMMARY"] = True
            if quest_status & 0x2:    quest_status_info["CURRENT_SUMMARY"] = True
            if quest_status & 0x4:    quest_status_info["RESISTANCE_SUMMARY"] = True
            if quest_status & 0x8:    quest_status_info["TEMPERATURE_SUMMARY"] = True
            if quest_status & 0x10:   quest_status_info["HUMIDITY_SUMMARY"] = True
            if quest_status & 0x800:  quest_status_info["QUESTIONABLE_CALIBRATION"] = True

            # Parse standard event register meanings
            event_status_info = {}
            if event_status & 0x1:   event_status_info["OPERATION_COMPLETE"] = True
            if event_status & 0x2:   event_status_info["REQUEST_CONTROL"] = True
            if event_status & 0x4:   event_status_info["QUERY_ERROR"] = True
            if event_status & 0x8:   event_status_info["DEVICE_ERROR"] = True
            if event_status & 0x10:  event_status_info["EXECUTION_ERROR"] = True
            if event_status & 0x20:  event_status_info["COMMAND_ERROR"] = True
            if event_status & 0x40:  event_status_info["USER_REQUEST"] = True
            if event_status & 0x80:  event_status_info["POWER_ON"] = True

            # Return dict with all status information
            status = {
                "measurement": {
                    "value": meas_status,
                    "info": meas_status_info
                },
                "operation": {
                    "value": op_status,
                    "info": op_status_info
                },
                "questionable": {
                    "value": quest_status,
                    "info": quest_status_info
                },
                "event": {
                    "value": event_status,
                    "info": event_status_info
                }
            }

            return status
        except Exception as e:
            bashlog.error(f"Error reading status registers: {e}")
            return {}

    async def perform_custom_measurement_sequence(self, voltage_levels, measurement_time=1.0):
        """Perform custom measurement sequence

        Args:
            voltage_levels: List of voltage values
            measurement_time: Time to dwell at each voltage point

        Returns:
            list: List of measurement results
        """
        results = []

        try:
            # Set up as voltage source
            await self.setup_as_voltage_source()

            # Enable output
            await self.output_on()

            for voltage in voltage_levels:
                # Set voltage
                await self.set_voltage(voltage)

                # Wait for stabilization
                await asyncio.sleep(measurement_time)

                # Take measurement
                voltage, current = await self.read_iv()
                if voltage is not None and current is not None:
                    results.append((voltage, current))
                    bashlog.info(f"Measurement point: V={voltage}V, I={current}A")

            # Turn off output
            await self.output_off()

            # Save results to file
            if results:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"custom_measurement_{timestamp}.csv"
                with open(filename, 'w') as f:
                    f.write("Voltage(V),Current(A)\n")
                    for v, i in results:
                        f.write(f"{v},{i}\n")
                bashlog.info(f"Custom measurement sequence completed, results saved to {filename}")

            return results
        except Exception as e:
            bashlog.error(f"Error performing custom measurement sequence: {e}")
            # Ensure output is off
            await self.output_off()
            return []


async def validate_instrument(resource_name):
    """Validate if instrument is available

    Args:
        resource_name: VISA resource name

    Returns:
        str: Error message, empty string on success
    """
    try:
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()

        bashlog.info(f"Available VISA resources: {resources}")

        instr = rm.open_resource(resource_name)

        # Set serial parameters (if serial device)
        if resource_name.startswith("ASRL"):
            instr.baud_rate = 9600
            instr.data_bits = 8
            instr.stop_bits = pyvisa.constants.StopBits.one
            instr.parity = pyvisa.constants.Parity.none
            instr.flow_control = pyvisa.constants.VI_ASRL_FLOW_NONE
            instr.timeout = 5000

        # Verify it's a Keithley instrument
        idn = instr.query("*IDN?")
        if "KEITHLEY" not in idn.upper():
            return f"Device is not a Keithley instrument: {idn}"

        bashlog.info(f"Found Keithley instrument: {idn}")
        instr.close()
        rm.close()
        return ""
    except Exception as e:
        return f"Error validating instrument: {e}"


# Example usage
async def main():
    # Use appropriate device address
    resource_name = "ASRL/dev/ttyUSB1::INSTR"

    # Validate instrument
    error = await validate_instrument(resource_name)
    if error:
        bashlog.error(f"Instrument validation failed: {error}")
        return

    bashlog.info("Instrument validation successful, beginning test...")

    # Create instrument control object
    keithley = KeithleyInstrument("keithley2410", resource_name)

    try:
        # Connect to instrument
        if not await keithley.connect():
            bashlog.error("Failed to connect to instrument")
            return

        # Set up as voltage source
        await keithley.setup_as_voltage_source(voltage_range=20, voltage_level=0, current_compliance=0.1)

        # Set up auto-zero and measurement range synchronization
        await keithley.setup_auto_zero("ON")  # Enable auto-zero
        await keithley.setup_sense_range_sync(True)  # Enable range synchronization

        # Set output off mode
        await keithley.set_output_off_mode("HIMPedance")  # High impedance state when off

        # Set data format
        await keithley.set_data_format(
            elements=["VOLTage", "CURRent", "TIME", "STATus"],  # Specify required data elements
            format_type="ASCii"  # Use ASCII format
        )

        # Set measurement speed
        await keithley.setup_measurement_speed(nplc=1.0)

        # Turn on output and set voltage
        await keithley.set_voltage(2.0)
        await keithley.output_on()

        # Read IV values
        voltage, current = await keithley.read_iv()
        bashlog.info(f"Measurement result: {voltage}V, {current}A")

        # Check status
        status = await keithley.read_status_registers()
        bashlog.info("Instrument status:")
        for category, info in status.items():
            if info['info']:  # Only show statuses with values
                bashlog.info(f"  {category.capitalize()} status: {info['info']}")

        bashlog.info("[INFO] check status. Sleep for 3 seconds.")
        time.sleep(3)

        # Check if in compliance state
        v_tripped, i_tripped = await keithley.check_compliance_state()
        if v_tripped or i_tripped:
            bashlog.info("Warning: Instrument is in compliance state")

        # Turn off output
        await keithley.output_off()

        # Perform IV sweep
        bashlog.info("Performing IV sweep...")
        results = await keithley.perform_iv_sweep(0, 5, points=11, use_buffer=True)

        if results:
            bashlog.info(f"Sweep yielded {len(results)} data points")

        # Perform custom measurement sequence
        bashlog.info("Performing custom measurement sequence...")
        custom_voltages = [0, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0]
        custom_results = await keithley.perform_custom_measurement_sequence(custom_voltages, measurement_time=2.0)

        if custom_results:
            bashlog.info(f"Custom measurement yielded {len(custom_results)} data points")

        bashlog.info("[INFO] perform_custom_measurement_sequence() done. Sleep for 3 seconds.")
        time.sleep(3)

        # Start IV monitoring and save data
        bashlog.info("Starting IV monitoring...")
        await keithley.set_voltage(2.5)
        await keithley.output_on()
        await keithley.start_iv_monitor(interval=1.0, save_data=True, max_samples=100)

        # Run for a while
        bashlog.info("IV monitoring in progress...")
        await asyncio.sleep(5)

        # Stop monitoring and get data
        success, monitor_data = await keithley.stop_iv_monitor()
        if success and monitor_data:
            bashlog.info(f"Successfully acquired {len(monitor_data)} monitoring data points")

        await keithley.output_off()

        bashlog.info("Test complete!")
    except Exception as e:
        bashlog.error(f"Error running test: {e}")
    finally:
        # Close connection
        await keithley.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
