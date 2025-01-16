import spidev
import time
import logging
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Pin Definitions for GPIO
PINS = {
    'RST': 26,  # Reset Pin
    'SDI': 10,  # SPI Data In
    'SDO': 9,   # SPI Data Out
    'CS': 8,    # Chip Select
    'SCLK': 11  # SPI Clock
}

class ATM90E3x:
    # Register Addresses (from datasheet)
    REGISTERS = {
        'VoltageRMS': 0x00D9,
        'CurrentRMS': 0x00DD,
        'ActivePower': 0xD0,
        'TotalEnergy': 0xD4,
        'PowerFactor': 0xD6,
        'PhaseAngle': 0xF9,
        'Freq': 0xF8,
        # Add additional registers as needed
    }

    DEFAULT_SPI_BUS = 0
    DEFAULT_SPI_DEVICE = 0
    DEFAULT_SPEED_HZ = 100000

    def __init__(self, spi_bus=DEFAULT_SPI_BUS, spi_device=DEFAULT_SPI_DEVICE, speed_hz=DEFAULT_SPEED_HZ):
        """Initialize the SPI connection and GPIO pin assignments."""
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        self.speed_hz = speed_hz

        try:
            self.spi = spidev.SpiDev()
            self.spi.open(spi_bus, spi_device)
            self.spi.max_speed_hz = speed_hz
            self.spi.mode = 0b00  # SPI Mode 0
            logging.info("ATM90E3x initialized with SPI bus %d, device %d, speed %d Hz", spi_bus, spi_device, speed_hz)

            self._init_gpio()
            self.reset_device()
        except Exception as e:
            logging.error("Failed to initialize SPI connection or GPIO: %s", e)
            raise RuntimeError("Initialization failed") from e

    def _init_gpio(self):
        """Initialize GPIO pins for the ATM90E3x."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PINS['RST'], GPIO.OUT)
        GPIO.output(PINS['RST'], GPIO.HIGH)  # Set reset pin high initially
        logging.info("GPIO initialized.")

    def reset_device(self):
        """Reset the ATM90E3x device."""
        GPIO.output(PINS['RST'], GPIO.LOW)
        time.sleep(0.1)  # Hold reset for 100ms
        GPIO.output(PINS['RST'], GPIO.HIGH)
        time.sleep(0.1)  # Allow the device to stabilize
        logging.info("Device reset complete.")

    def _spi_transfer(self, data):
        """Perform an SPI transfer."""
        try:
            logging.debug("Sending SPI data: %s", data)
            response = self.spi.xfer2(data)
            logging.debug("SPI transfer: Sent %s, Received %s", data, response)
            return response
        except Exception as e:
            logging.error("SPI transfer failed: %s", e)
            raise RuntimeError("SPI transfer failed") from e

    def _read_register(self, register_name):
        """Read data from a register."""
        if register_name not in self.REGISTERS:
            raise ValueError(f"Unknown register: {register_name}")
        
        reg_address = self.REGISTERS[register_name]
        cmd = [0x80 | (reg_address >> 8), reg_address & 0xFF, 0x00, 0x00]
        response = self._spi_transfer(cmd)
        
        if len(response) != 4:
            raise RuntimeError("Invalid response length")

        result = (response[2] << 8) | response[3]
        logging.debug("Read register %s (0x%04X): 0x%04X", register_name, reg_address, result)
        return result

    def _write_register(self, register_name, value):
        """Write data to a register."""
        if register_name not in self.REGISTERS:
            raise ValueError(f"Unknown register: {register_name}")
        
        reg_address = self.REGISTERS[register_name]
        cmd = [reg_address >> 8, reg_address & 0xFF, value >> 8, value & 0xFF]
        self._spi_transfer(cmd)
        logging.debug("Wrote 0x%04X to register %s (0x%04X)", value, register_name, reg_address)

    # Reading specific parameters
    def read_voltage(self):
        """Read RMS Voltage."""
        return self._read_register('VoltageRMS') * 0.01

    def read_current(self):
        """Read RMS Current."""
        return self._read_register('CurrentRMS') * 0.001

    def read_power(self):
        """Read Active Power."""
        return self._read_register('ActivePower') * 0.01

    def read_energy(self):
        """Read Total Energy."""
        return self._read_register('TotalEnergy') * 0.001

    def read_power_factor(self):
        """Read Power Factor."""
        return self._read_register('PowerFactor') * 0.001

    def read_phase_angle(self):
        """Read Phase Angle."""
        return self._read_register('PhaseAngle') * 0.01

    def read_frequency(self):
        """Read Frequency."""
        return self._read_register('Freq') * 0.01

    def close(self):
        """Close the SPI connection and reset GPIO pins."""
        try:
            self.spi.close()
            GPIO.cleanup()
            logging.info("SPI connection closed and GPIO cleaned up.")
        except Exception as e:
            logging.error("Error closing resources: %s", e)
            raise RuntimeError("Failed to close resources") from e

# Example Usage
def main():
    meter = ATM90E3x()
    try:
        print(f"Voltage: {meter.read_voltage()} V")
        print(f"Current: {meter.read_current()} A")
        print(f"Power: {meter.read_power()} W")
        print(f"Energy: {meter.read_energy()} kWh")
        print(f"Power Factor: {meter.read_power_factor()}")
        print(f"Phase Angle: {meter.read_phase_angle()} degrees")
        print(f"Frequency: {meter.read_frequency()} Hz")
    finally:
        meter.close()

if __name__ == "__main__":
    main()

