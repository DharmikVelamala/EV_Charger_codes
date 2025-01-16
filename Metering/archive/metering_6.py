import spidev
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ATM90E3x:
    # Register Addresses
    REG_VOLTAGE = 0x0001
    REG_CURRENT = 0x0002
    REG_POWER = 0x0003
    REG_ENERGY = 0x0004
    REG_RESET_ENERGY = 0x0005
    REG_POWER_FACTOR = 0x0006
    REG_PHASE_ANGLE = 0x0007
    REG_VOLTAGE_CAL = 0x0100
    REG_CURRENT_CAL = 0x0101
    REG_STATUS_FLAGS = 0x0200
    REG_CLEAR_FLAGS = 0x0201

    # Default pin assignments (Raspberry Pi pins)
    DEFAULT_SPI_BUS = 0
    DEFAULT_SPI_DEVICE = 0
    DEFAULT_SPEED_HZ = 50000
    DEFAULT_VOLTAGE_CAL = 0x1234
    DEFAULT_CURRENT_CAL = 0x5678
    
    # GPIO pin assignments for energy monitoring
    PIN_RESET_ENERGY = 17  # Example GPIO pin for energy reset
    PIN_STATUS_FLAGS = 27  # Example GPIO pin for status flags

    def __init__(self, spi_bus=DEFAULT_SPI_BUS, spi_device=DEFAULT_SPI_DEVICE, speed_hz=DEFAULT_SPEED_HZ,
                 default_voltage_cal=DEFAULT_VOLTAGE_CAL, default_current_cal=DEFAULT_CURRENT_CAL):
        """
        Initialize the SPI connection and GPIO pin assignments.

        :param spi_bus: SPI bus number.
        :param spi_device: SPI device number.
        :param speed_hz: SPI communication speed.
        :param default_voltage_cal: Default voltage calibration value.
        :param default_current_cal: Default current calibration value.
        """
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(spi_bus, spi_device)
            self.spi.max_speed_hz = speed_hz
            self.spi.mode = 0b00  # SPI Mode 0
            self.default_voltage_cal = default_voltage_cal
            self.default_current_cal = default_current_cal
            logging.info("ATM90E3x initialized with SPI bus %d, device %d, speed %d Hz", spi_bus, spi_device, speed_hz)

            # Setup GPIO pins for reset and status flags
            self._setup_gpio()

        except Exception as e:
            logging.error("Failed to initialize SPI connection: %s", e)
            raise RuntimeError("SPI initialization failed") from e

    def _setup_gpio(self):
        """Set up the GPIO pins for reset and status flags."""
        try:
            # Assuming you're using the RPi.GPIO library
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.PIN_RESET_ENERGY, GPIO.OUT)
            GPIO.setup(self.PIN_STATUS_FLAGS, GPIO.IN)
            logging.info("GPIO pins set up for reset and status flags.")
        except ImportError:
            logging.error("RPi.GPIO library is required for GPIO setup.")
            raise RuntimeError("GPIO setup failed")

    def close(self):
        """Close the SPI connection and reset GPIO pins."""
        try:
            self.spi.close()
            logging.info("SPI connection closed.")
            # Reset GPIO pins when closing
            import RPi.GPIO as GPIO
            GPIO.cleanup()
            logging.info("GPIO cleanup done.")
        except Exception as e:
            logging.error("Error closing SPI connection or GPIO cleanup: %s", e)
            raise RuntimeError("Failed to close SPI connection or GPIO cleanup") from e

    def _spi_transfer(self, data):
        """
        Perform an SPI transfer.

        :param data: List of bytes to send.
        :return: List of bytes received.
        """
        try:
            response = self.spi.xfer2(data)
            logging.debug("SPI transfer: Sent %s, Received %s", data, response)
            return response
        except Exception as e:
            logging.error("SPI transfer failed: %s", e)
            raise RuntimeError("SPI transfer failed") from e

    def _read_register(self, register_address):
        """
        Read data from a register.

        :param register_address: Address of the register to read.
        :return: Value of the register.
        """
        try:
            cmd = [0x80 | (register_address >> 8), register_address & 0xFF, 0x00, 0x00]
            response = self._spi_transfer(cmd)
            if len(response) != 4:
                raise ValueError("Unexpected response length")
            value = (response[2] << 8) | response[3]
            logging.debug("Read register 0x%04X: 0x%04X", register_address, value)
            return value
        except Exception as e:
            logging.error("Error reading register 0x%04X: %s", register_address, e)
            raise RuntimeError(f"Failed to read register 0x{register_address:04X}") from e

    def _write_register(self, register_address, value):
        """
        Write data to a register.

        :param register_address: Address of the register to write.
        :param value: 16-bit value to write.
        """
        try:
            cmd = [register_address >> 8, register_address & 0xFF, value >> 8, value & 0xFF]
            self._spi_transfer(cmd)
            logging.debug("Wrote 0x%04X to register 0x%04X", value, register_address)
        except Exception as e:
            logging.error("Error writing to register 0x%04X: %s", register_address, e)
            raise RuntimeError(f"Failed to write to register 0x{register_address:04X}") from e

    def read_voltage(self):
        """Read RMS Voltage."""
        try:
            voltage = self._read_register(self.REG_VOLTAGE) * 0.01
            logging.info("Voltage: %.2f V", voltage)
            return voltage
        except Exception as e:
            logging.error("Error reading voltage: %s", e)
            raise

    def read_current(self):
        """Read RMS Current."""
        try:
            current = self._read_register(self.REG_CURRENT) * 0.001
            logging.info("Current: %.3f A", current)
            return current
        except Exception as e:
            logging.error("Error reading current: %s", e)
            raise

    def read_power(self):
        """Read Active Power."""
        try:
            power = self._read_register(self.REG_POWER) * 0.01
            logging.info("Power: %.2f W", power)
            return power
        except Exception as e:
            logging.error("Error reading power: %s", e)
            raise

    def read_energy(self):
        """Read Total Energy."""
        try:
            energy = self._read_register(self.REG_ENERGY) * 0.001
            logging.info("Energy: %.3f kWh", energy)
            return energy
        except Exception as e:
            logging.error("Error reading energy: %s", e)
            raise

    def reset_energy(self):
        """Reset energy accumulator."""
        try:
            self._write_register(self.REG_RESET_ENERGY, 0xFFFF)
            logging.info("Energy accumulator reset.")
            # Use GPIO to reset energy if necessary
            import RPi.GPIO as GPIO
            GPIO.output(self.PIN_RESET_ENERGY, GPIO.HIGH)  # Trigger reset signal
            time.sleep(1)
            GPIO.output(self.PIN_RESET_ENERGY, GPIO.LOW)  # Reset pin to LOW
        except Exception as e:
            logging.error("Error resetting energy accumulator: %s", e)
            raise

    def read_power_factor(self):
        """Read Power Factor."""
        try:
            power_factor = self._read_register(self.REG_POWER_FACTOR) * 0.001
            logging.info("Power Factor: %.3f", power_factor)
            return power_factor
        except Exception as e:
            logging.error("Error reading power factor: %s", e)
            raise

    def read_phase_angle(self):
        """Read Phase Angle."""
        try:
            phase_angle = self._read_register(self.REG_PHASE_ANGLE) * 0.01
            logging.info("Phase Angle: %.2f degrees", phase_angle)
            return phase_angle
        except Exception as e:
            logging.error("Error reading phase angle: %s", e)
            raise

    def calibrate_voltage(self, calibration_value=None):
        """Calibrate Voltage Measurement."""
        try:
            calibration_value = calibration_value or self.default_voltage_cal
            self._write_register(self.REG_VOLTAGE_CAL, calibration_value)
            logging.info("Voltage calibrated with value 0x%04X", calibration_value)
        except Exception as e:
            logging.error("Error calibrating voltage: %s", e)
            raise

    def calibrate_current(self, calibration_value=None):
        """Calibrate Current Measurement."""
        try:
            calibration_value = calibration_value or self.default_current_cal
            self._write_register(self.REG_CURRENT_CAL, calibration_value)
            logging.info("Current calibrated with value 0x%04X", calibration_value)
        except Exception as e:
            logging.error("Error calibrating current: %s", e)
            raise

    def get_status_flags(self):
        """Read Status Flags."""
        try:
            status = self._read_register(self.REG_STATUS_FLAGS)
            logging.info("Status Flags: 0x%04X", status)
            return status
        except Exception as e:
            logging.error("Error reading status flags: %s", e)
            raise

    def clear_status_flags(self):
        """Clear Status Flags."""
        try:
            self._write_register(self.REG_CLEAR_FLAGS, 0xFFFF)
            logging.info("Status flags cleared.")
        except Exception as e:
            logging.error("Error clearing status flags: %s", e)
            raise

# Example Usage
def main():
    meter = ATM90E3x(spi_bus=0, spi_device=0, speed_hz=50000)
    try:
        voltage = meter.read_voltage()
        current = meter.read_current()
        power = meter.read_power()
        energy = meter.read_energy()
        power_factor = meter.read_power_factor()
        phase_angle = meter.read_phase_angle()

        print(f"Voltage: {voltage} V")
        print(f"Current: {current} A")
        print(f"Power: {power} W")
        print(f"Energy: {energy} kWh")
        print(f"Power Factor: {power_factor}")
        print(f"Phase Angle: {phase_angle} degrees")

        # Example of calibration
        meter.calibrate_voltage()
        meter.calibrate_current()

        # Reading and clearing status flags
        status = meter.get_status_flags()
        print(f"Status Flags: {status}")
        meter.clear_status_flags()

        # Resetting energy with GPIO signal
        meter.reset_energy()

    finally:
        meter.close()

if __name__ == "__main__":
    main()
