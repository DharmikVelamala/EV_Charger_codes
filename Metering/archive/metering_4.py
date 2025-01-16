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

    def __init__(self, spi_bus=0, spi_device=0, speed_hz=50000, default_voltage_cal=0x1234, default_current_cal=0x5678):
        """
        Initialize the SPI connection.

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
        except Exception as e:
            logging.error("Failed to initialize SPI connection: %s", e)
            raise

    def close(self):
        """Close the SPI connection."""
        try:
            self.spi.close()
            logging.info("SPI connection closed.")
        except Exception as e:
            logging.error("Error closing SPI connection: %s", e)

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
            raise

    def _read_register(self, register_address):
        """
        Read data from a register.

        :param register_address: Address of the register to read.
        :return: Value of the register.
        """
        try:
            cmd = [0x80 | (register_address >> 8), register_address & 0xFF, 0x00, 0x00]
            response = self._spi_transfer(cmd)
            value = (response[2] << 8) | response[3]
            logging.debug("Read register 0x%04X: 0x%04X", register_address, value)
            return value
        except Exception as e:
            logging.error("Error reading register 0x%04X: %s", register_address, e)
            raise

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
            raise

    def read_voltage(self):
        """Read RMS Voltage."""
        voltage = self._read_register(self.REG_VOLTAGE) * 0.01
        logging.info("Voltage: %.2f V", voltage)
        return voltage

    def read_current(self):
        """Read RMS Current."""
        current = self._read_register(self.REG_CURRENT) * 0.001
        logging.info("Current: %.3f A", current)
        return current

    def read_power(self):
        """Read Active Power."""
        power = self._read_register(self.REG_POWER) * 0.01
        logging.info("Power: %.2f W", power)
        return power

    def read_energy(self):
        """Read Total Energy."""
        energy = self._read_register(self.REG_ENERGY) * 0.001
        logging.info("Energy: %.3f kWh", energy)
        return energy

    def reset_energy(self):
        """Reset energy accumulator."""
        self._write_register(self.REG_RESET_ENERGY, 0xFFFF)
        logging.info("Energy accumulator reset.")

    def read_power_factor(self):
        """Read Power Factor."""
        power_factor = self._read_register(self.REG_POWER_FACTOR) * 0.001
        logging.info("Power Factor: %.3f", power_factor)
        return power_factor

    def read_phase_angle(self):
        """Read Phase Angle."""
        phase_angle = self._read_register(self.REG_PHASE_ANGLE) * 0.01
        logging.info("Phase Angle: %.2f degrees", phase_angle)
        return phase_angle

    def calibrate_voltage(self, calibration_value=None):
        """Calibrate Voltage Measurement."""
        calibration_value = calibration_value or self.default_voltage_cal
        self._write_register(self.REG_VOLTAGE_CAL, calibration_value)
        logging.info("Voltage calibrated with value 0x%04X", calibration_value)

    def calibrate_current(self, calibration_value=None):
        """Calibrate Current Measurement."""
        calibration_value = calibration_value or self.default_current_cal
        self._write_register(self.REG_CURRENT_CAL, calibration_value)
        logging.info("Current calibrated with value 0x%04X", calibration_value)

    def get_status_flags(self):
        """Read Status Flags."""
        status = self._read_register(self.REG_STATUS_FLAGS)
        logging.info("Status Flags: 0x%04X", status)
        return status

    def clear_status_flags(self):
        """Clear Status Flags."""
        self._write_register(self.REG_CLEAR_FLAGS, 0xFFFF)
        logging.info("Status flags cleared.")

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
    finally:
        meter.close()

if __name__ == "__main__":
    main()
