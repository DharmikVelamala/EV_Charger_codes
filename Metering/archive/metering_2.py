import spidev
import time

class ATM90E3x:
    def __init__(self, spi_bus=0, spi_device=0, speed_hz=50000):
        """
        Initialize the SPI connection.

        :param spi_bus: SPI bus number.
        :param spi_device: SPI device number.
        :param speed_hz: SPI communication speed.
        """
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = speed_hz
        self.spi.mode = 0b00  # SPI Mode 0

    def close(self):
        """Close the SPI connection."""
        self.spi.close()

    def _spi_transfer(self, data):
        """
        Perform an SPI transfer.

        :param data: List of bytes to send.
        :return: List of bytes received.
        """
        return self.spi.xfer2(data)

    def _read_register(self, register_address):
        """
        Read data from a register.

        :param register_address: Address of the register to read.
        :return: Value of the register.
        """
        # MSB: Read Command (0x80) | Register Address
        cmd = [0x80 | (register_address >> 8), register_address & 0xFF, 0x00, 0x00]
        response = self._spi_transfer(cmd)
        # Combine the response bytes
        return (response[2] << 8) | response[3]

    def _write_register(self, register_address, value):
        """
        Write data to a register.

        :param register_address: Address of the register to write.
        :param value: 16-bit value to write.
        """
        # MSB: Write Command (0x00) | Register Address
        cmd = [register_address >> 8, register_address & 0xFF, value >> 8, value & 0xFF]
        self._spi_transfer(cmd)

    def read_voltage(self):
        """Read RMS Voltage."""
        return self._read_register(0x0001) * 0.01  # Example scaling factor

    def read_current(self):
        """Read RMS Current."""
        return self._read_register(0x0002) * 0.001

    def read_power(self):
        """Read Active Power."""
        return self._read_register(0x0003) * 0.01

    def read_energy(self):
        """Read Total Energy."""
        return self._read_register(0x0004) * 0.001

    def reset_energy(self):
        """Reset energy accumulator."""
        self._write_register(0x0005, 0xFFFF)

    def read_power_factor(self):
        """Read Power Factor."""
        return self._read_register(0x0006) * 0.001

    def read_phase_angle(self):
        """Read Phase Angle."""
        return self._read_register(0x0007) * 0.01

    def calibrate_voltage(self, calibration_value):
        """Calibrate Voltage Measurement."""
        self._write_register(0x0100, calibration_value)

    def calibrate_current(self, calibration_value):
        """Calibrate Current Measurement."""
        self._write_register(0x0101, calibration_value)

    def get_status_flags(self):
        """Read Status Flags."""
        return self._read_register(0x0200)

    def clear_status_flags(self):
        """Clear Status Flags."""
        self._write_register(0x0201, 0xFFFF)

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
        meter.calibrate_voltage(0x1234)
        meter.calibrate_current(0x5678)

        # Reading and clearing status flags
        status = meter.get_status_flags()
        print(f"Status Flags: {status}")
        meter.clear_status_flags()
    finally:
        meter.close()

if __name__ == "__main__":
    main()
