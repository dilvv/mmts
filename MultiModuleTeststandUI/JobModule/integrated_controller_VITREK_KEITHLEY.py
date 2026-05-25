import asyncio
import os
import json
from datetime import datetime
from pathlib import Path

class IntegratedTestController:
    """
    Integrated controller for coordinating Vitrek 964i switch and Keithley SourceMeter operations.

    This class provides methods to control both the Vitrek 964i switching system and
    a Keithley SourceMeter, allowing coordinated operations like IV curve scanning
    across multiple channels/modules.
    """

    def __init__(self, switch_resource, keithley_resource):
        """
        Initialize the integrated controller

        Args:
            switch_resource: VISA resource name for Vitrek 964i (e.g., "ASRL/dev/ttyUSB0::INSTR")
            keithley_resource: VISA resource name for Keithley SourceMeter (e.g., "GPIB0::24::INSTR")
        """
        # Import here to avoid circular imports
        from device_VITREK_switch_control import Vitrek964i
        from device_KEITHLEY_power_supply import KeithleyInstrument

        self.switch = Vitrek964i(switch_resource)
        self.keithley = KeithleyInstrument("keithley", keithley_resource)

        # Directory for saving results
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)

        # Tracking currently active module/channel
        self.current_bank = None
        self.current_relay = None
        self.current_module_id = None

    async def connect_all(self):
        """
        Connect to both the Vitrek switch and Keithley SourceMeter

        Returns:
            bool: True if both devices connected successfully, False otherwise
        """
        print("Connecting to Vitrek 964i switch...")
        switch_connected = await self.switch.connect()

        print("Connecting to Keithley SourceMeter...")
        keithley_connected = await self.keithley.connect()

        if switch_connected and keithley_connected:
            print("Both devices connected successfully")
            return True
        else:
            if not switch_connected:
                print("Failed to connect to Vitrek 964i")
            if not keithley_connected:
                print("Failed to connect to Keithley SourceMeter")
            return False

    async def disconnect_all(self):
        """
        Safely disconnect from all devices
        """
        # Turn off SourceMeter output first for safety
        try:
            await self.keithley.output_off()
            print("Keithley output turned off")
        except Exception as e:
            print(f"Error turning off Keithley output: {e}")

        # Then disconnect from both devices
        try:
            await self.keithley.disconnect()
            print("Disconnected from Keithley")
        except Exception as e:
            print(f"Error disconnecting from Keithley: {e}")

        try:
            self.switch.disconnect()
            print("Disconnected from Vitrek switch")
        except Exception as e:
            print(f"Error disconnecting from Vitrek switch: {e}")

    async def initialize_keithley_for_iv_scan(self, voltage_range=20, current_compliance=0.1):
        """
        Set up the Keithley SourceMeter for IV scanning

        Args:
            voltage_range: Maximum voltage range for the test
            current_compliance: Current compliance limit in amps

        Returns:
            bool: True if initialization was successful
        """
        try:
            # Reset the instrument
            await self.keithley.reset()

            # Configure as voltage source for IV scanning
            await self.keithley.setup_as_voltage_source(
                voltage_range=voltage_range,
                voltage_level=0,  # Start at 0V
                current_compliance=current_compliance
            )

            # Configure measurement settings
            await self.keithley.setup_measurement_speed(nplc=1.0)  # 1 PLC for balance of speed/accuracy
            await self.keithley.setup_auto_zero("ON")
            await self.keithley.setup_sense_range_sync(True)

            # Set appropriate output-off mode
            await self.keithley.set_output_off_mode("HIMPedance")

            # Configure data format for measurements
            await self.keithley.set_data_format(
                elements=["VOLTage", "CURRent", "TIME", "STATus"],
                format_type="ASCii"
            )

            print(f"Keithley initialized for IV scan (voltage range: {voltage_range}V, compliance: {current_compliance}A)")
            return True

        except Exception as e:
            print(f"Error initializing Keithley for IV scan: {e}")
            return False

    async def select_channel(self, bank, relay, module_id=None):
        """
        Select a specific channel on the Vitrek switch

        Args:
            bank: Bank number (0-7)
            relay: Relay number within the bank (1-8)
            module_id: Optional module identifier for this channel

        Returns:
            bool: True if channel was selected successfully
        """
        try:
            # First ensure all relays are open for safety
            await self.switch.reset()

            # Convert relay number (1-8) to a bit pattern for the bank
            # e.g., relay 1 -> 0x01, relay 2 -> 0x02, relay 3 -> 0x04, etc.
            relay_bit = 1 << (relay - 1)
            hex_state = f"#h{relay_bit:02X}"

            # Set only the specified relay in the bank
            await self.switch.set_bank_state(bank, hex_state)

            # Verify the relay state
            state = await self.switch.get_bank_state(bank)
            expected_state = hex_state.upper().replace(' ', '')
            if state.upper().replace(' ', '') != expected_state:
                print(f"Warning: Failed to set relay state properly. Expected {expected_state}, got {state}")
                return False

            # Update current channel tracking
            self.current_bank = bank
            self.current_relay = relay
            self.current_module_id = module_id

            print(f"Selected channel: Bank {bank}, Relay {relay}" +
                  (f" (Module ID: {module_id})" if module_id else ""))
            return True

        except Exception as e:
            print(f"Error selecting channel: {e}")
            return False

    def _generate_filename(self, test_type, file_extension="csv"):
        """
        Generate a filename for saving test results

        Args:
            test_type: Type of test (e.g., 'iv_scan', 'diode_test')
            file_extension: File extension (default: 'csv')

        Returns:
            str: Formatted filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Include bank, relay, and module ID in filename if available
        parts = [timestamp]

        if self.current_bank is not None:
            parts.append(f"bank{self.current_bank}")

        if self.current_relay is not None:
            parts.append(f"relay{self.current_relay}")

        if self.current_module_id:
            # Remove any characters that would be invalid in a filename
            safe_module_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(self.current_module_id))
            parts.append(f"module_{safe_module_id}")

        parts.append(test_type)

        filename = "_".join(parts) + f".{file_extension}"
        return os.path.join(self.results_dir, filename)

    async def perform_iv_scan(self, start_v, stop_v, points=21, module_id=None):
        """
        Perform an IV scan on the currently selected channel

        Args:
            start_v: Starting voltage
            stop_v: Ending voltage
            points: Number of points in the scan
            module_id: Optional module identifier (overrides current module ID)

        Returns:
            tuple: (success, filename) - Success status and path to results file if successful
        """
        if module_id:
            self.current_module_id = module_id

        # Check if a channel is selected
        if self.current_bank is None or self.current_relay is None:
            print("Error: No channel selected. Use select_channel() first.")
            return False, None

        try:
            # Get results filename
            filename = self._generate_filename("iv_scan")

            print(f"Starting IV scan from {start_v}V to {stop_v}V with {points} points...")

            # Use the Keithley's built-in IV scan function
            results = await self.keithley.perform_iv_sweep(
                start_v=start_v,
                stop_v=stop_v,
                points=points,
                use_buffer=True
            )

            if not results:
                print("Error: IV scan failed to return results")
                return False, None

            # Save results to our own custom-named file
            with open(filename, 'w') as f:
                f.write("Voltage(V),Current(A)\n")
                for v, i in results:
                    f.write(f"{v},{i}\n")

            print(f"IV scan completed with {len(results)} points, saved to {filename}")
            return True, filename

        except Exception as e:
            print(f"Error performing IV scan: {e}")
            # Make sure output is off
            await self.keithley.output_off()
            return False, None

    async def run_batch_iv_scan(self, config_file=None, bank_relay_pairs=None,
                               start_v=0, stop_v=1, points=21,
                               module_mapping=None):
        """
        Run IV scans on multiple channels sequentially

        Args:
            config_file: Optional JSON file with test configuration
            bank_relay_pairs: List of (bank, relay) tuples to test
            start_v: Starting voltage for IV scans
            stop_v: Ending voltage for IV scans
            points: Number of points in each IV scan
            module_mapping: Dict mapping (bank, relay) tuples to module IDs

        Returns:
            dict: Results with channels as keys and filenames as values
        """
        results = {}

        # Load configuration from file if provided
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)

                # Override parameters with those from config file
                start_v = config.get("start_v", start_v)
                stop_v = config.get("stop_v", stop_v)
                points = config.get("points", points)

                # Get bank/relay pairs from config if not provided
                if not bank_relay_pairs and "channels" in config:
                    bank_relay_pairs = []
                    for channel in config["channels"]:
                        bank = channel.get("bank")
                        relay = channel.get("relay")
                        if bank is not None and relay is not None:
                            bank_relay_pairs.append((bank, relay))

                # Get module mapping from config if not provided
                if not module_mapping and "channels" in config:
                    module_mapping = {}
                    for channel in config["channels"]:
                        bank = channel.get("bank")
                        relay = channel.get("relay")
                        module_id = channel.get("module_id")
                        if bank is not None and relay is not None and module_id:
                            module_mapping[(bank, relay)] = module_id

                print(f"Loaded configuration from {config_file}")

            except Exception as e:
                print(f"Error loading configuration file: {e}")
                return results

        # Initialize Keithley for IV scanning
        if not await self.initialize_keithley_for_iv_scan():
            print("Failed to initialize Keithley for IV scanning")
            return results

        # Make sure we have channels to test
        if not bank_relay_pairs:
            print("No channels specified for testing")
            return results

        print(f"Starting batch IV scan on {len(bank_relay_pairs)} channels...")

        try:
            # Process each channel
            for bank, relay in bank_relay_pairs:
                # Get module ID if available
                module_id = module_mapping.get((bank, relay)) if module_mapping else None

                print(f"\nTesting Bank {bank}, Relay {relay}" +
                      (f" (Module ID: {module_id})" if module_id else ""))

                # Select the channel
                if not await self.select_channel(bank, relay, module_id):
                    print(f"Skipping Bank {bank}, Relay {relay} due to selection failure")
                    continue

                # Allow the relay to settle
                await asyncio.sleep(0.5)

                # Perform IV scan on this channel
                success, filename = await self.perform_iv_scan(start_v, stop_v, points)

                if success:
                    results[(bank, relay)] = filename
                else:
                    print(f"IV scan failed for Bank {bank}, Relay {relay}")

                # Ensure output is off before switching channels
                await self.keithley.output_off()

                # Pause between tests
                await asyncio.sleep(0.5)

        except Exception as e:
            print(f"Error during batch IV scan: {e}")
        finally:
            # Clean up
            await self.keithley.output_off()
            await self.switch.reset()

        print(f"\nBatch IV scan completed. Tested {len(results)}/{len(bank_relay_pairs)} channels successfully.")
        return results

    async def create_config_file(self, filename="iv_scan_config.json", bank_relay_pairs=None,
                               module_mapping=None, start_v=0, stop_v=1, points=21):
        """
        Create a configuration file for batch testing

        Args:
            filename: Name of the config file to create
            bank_relay_pairs: List of (bank, relay) tuples to include
            module_mapping: Dict mapping (bank, relay) tuples to module IDs
            start_v: Starting voltage for IV scans
            stop_v: Ending voltage for IV scans
            points: Number of points in each IV scan

        Returns:
            bool: True if file created successfully
        """
        try:
            # Prepare the configuration dictionary
            config = {
                "start_v": start_v,
                "stop_v": stop_v,
                "points": points,
                "channels": []
            }

            # Add channel information
            if bank_relay_pairs:
                for bank, relay in bank_relay_pairs:
                    channel = {
                        "bank": bank,
                        "relay": relay
                    }

                    # Add module ID if available
                    if module_mapping and (bank, relay) in module_mapping:
                        channel["module_id"] = module_mapping[(bank, relay)]

                    config["channels"].append(channel)

            # Write to file
            with open(filename, 'w') as f:
                json.dump(config, f, indent=4)

            print(f"Configuration file created: {filename}")
            return True

        except Exception as e:
            print(f"Error creating configuration file: {e}")
            return False

    async def test_module_series(self, bank, start_relay, end_relay,
                               module_id_prefix="MOD", start_id=1,
                               start_v=0, stop_v=1, points=21):
        """
        Test a series of modules with sequential module IDs

        Args:
            bank: Bank number to use for all modules
            start_relay: First relay number
            end_relay: Last relay number (inclusive)
            module_id_prefix: Prefix for module IDs
            start_id: Starting module ID number
            start_v: Starting voltage for IV scans
            stop_v: Ending voltage for IV scans
            points: Number of points in each IV scan

        Returns:
            dict: Results with channels as keys and filenames as values
        """
        # Generate bank/relay pairs
        bank_relay_pairs = [(bank, relay) for relay in range(start_relay, end_relay + 1)]

        # Generate module mapping
        module_mapping = {}
        for i, (bank, relay) in enumerate(bank_relay_pairs):
            module_mapping[(bank, relay)] = f"{module_id_prefix}{start_id + i}"

        # Run the batch test
        return await self.run_batch_iv_scan(
            bank_relay_pairs=bank_relay_pairs,
            module_mapping=module_mapping,
            start_v=start_v,
            stop_v=stop_v,
            points=points
        )


# Example usage
async def main():
    # Create controller with appropriate resource names
    controller = IntegratedTestController(
        keithley_resource="ASRL/dev/ttyUSB2::INSTR",
        switch_resource="ASRL/dev/ttyUSB1::INSTR",
    )

    try:
        # Connect to devices
        connected = await controller.connect_all()
        if not connected:
            print("Failed to connect to all devices")
            return

        # Example 1: Create configuration for batch testing
        await controller.create_config_file(
            filename="silicon_modules_test.json",
            bank_relay_pairs=[(0, 1), (0, 2), (0, 3)],
            module_mapping={(0, 1): "SN001", (0, 2): "SN002", (0, 3): "SN003"},
            start_v=0,
            stop_v=0.8,
            points=21
        )

        # Example 2: Run batch IV scan with module series
        results = await controller.test_module_series(
            bank=0,
            start_relay=1,
            end_relay=4,
            module_id_prefix="SN",
            start_id=101,
            start_v=0,
            stop_v=0.8,
            points=21
        )

        # Example 3: Run IV scan on a single channel
        await controller.select_channel(bank=0, relay=5, module_id="SN105")
        success, filename = await controller.perform_iv_scan(start_v=0, stop_v=0.8, points=21)

    except Exception as e:
        print(f"Test error: {e}")
    finally:
        # Always disconnect properly
        await controller.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
