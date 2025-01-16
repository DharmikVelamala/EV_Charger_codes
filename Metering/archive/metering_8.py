import spidev
import time
import logging
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Pin Definitions for GPIO
PINS = {
    'GND': "GND",
    'ZX0': 4,
    'ZX1': 17,
    'ZX2': 27,
    'CF1': 22,
    'CF2': 23,
    'CF3': 24,
    'CF4': 25,
    'WarnOut': 5,
    'IRQ0': 6,
    'IRQ1': 12,
    'PM0': 13,
    'PM1': 19,
    'DMA': 16,
    'SDI': 10,
    'CS': 8,
    'SCLK': 11,
    'SDO': 9,
    'EXT_VDD': "POWER",  # 3.3V power pin
    'RST': 25
}

class ATM90E3x:
    # Register Addresses
    REGISTERS = {
        'VoltageA': 0xD9,
        'VoltageB': 0xDA,
        'VoltageC': 0xDB,
        'CurrentA': 0xDD,
        'CurrentB': 0xDE,
        'CurrentC': 0xDF,
        'PowerA': 0xD1,
        'PowerB': 0xD2,
        'PowerC': 0xD3,
        'Frequency': 0xB8,
        'PhaseAngleA': 0xF9,
        'PhaseAngleB': 0xFA,
        'PhaseAngleC': 0xFB,
        'REG_VOLTAGE_CAL': 0x0100,
        'REG_CURRENT_CAL': 0x0101,
        # Add additional registers as needed
    }
    
    
    # Default pin assignments (Raspberry Pi pins)
    DEFAULT_SPI_BUS = 0
    DEFAULT_SPI_MODE = 0b11
    DEFAULT_SPI_DEVICE = 0
    DEFAULT_SPEED_HZ = 2000000
    DEFAULT_VOLTAGE_CAL = 0x1000
    DEFAULT_CURRENT_CAL = 0x1000

    def __init__(self, spi_bus=DEFAULT_SPI_BUS, spi_device=DEFAULT_SPI_DEVICE, speed_hz=DEFAULT_SPEED_HZ, spi_mode=DEFAULT_SPI_MODE):
        """Initialize SPI and GPIO for ATM90E3x."""
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        self.speed_hz = speed_hz
        
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(spi_bus, spi_device)
            self.spi.max_speed_hz = speed_hz
            self.spi.mode = spi_mode
            
            logging.info("ATM90E3x initialized on SPI bus %d, device %d", spi_bus, spi_device)
            
            self._init_gpio()
            self.reset_device()

        except Exception as e:
            logging.error("SPI initialization failed: %s", e)
            raise RuntimeError("Failed to initialize SPI") from e


    def reset_device(self):
        """Reset the ATM90E3x device."""
        try:
            GPIO.output(PINS['RST'], GPIO.LOW)
            time.sleep(0.1)  # Hold reset for 100ms
            GPIO.output(PINS['RST'], GPIO.HIGH)
            time.sleep(0.1)  # Allow the device to stabilize
            logging.info("Device reset complete.")
        except Exception as e:
            logging.error("Device reset failed: %s", e)
            raise RuntimeError("Device reset failed") from e


    def _init_gpio(self):
        """Set up GPIO pins for zero-crossing and interrupt requests."""
        GPIO.setwarnings(False)  # Suppress warnings
        GPIO.setmode(GPIO.BCM)
        try:
            
            logging.debug("Setting up GPIO RST")
            GPIO.setup(PINS['RST'], GPIO.OUT, initial=GPIO.HIGH)
            
            logging.debug("Setting up GPIO ZX0 and IRQ0")
            GPIO.setup(PINS['ZX0'], GPIO.IN)
            GPIO.setup(PINS['IRQ0'], GPIO.IN)
            
            logging.debug("Adding event detect for ZX0 and IRQ0")
            GPIO.add_event_detect(PINS['ZX0'], GPIO.RISING, callback=self._on_zero_crossing)
            GPIO.add_event_detect(PINS['IRQ0'], GPIO.FALLING, callback=self._on_interrupt_request)
            logging.info("GPIO pins set up for zero-crossing and interrupt requests.")
        except Exception as e:
            logging.error("Error setting up GPIO interrupts: %s", e)
            GPIO.cleanup() 
            raise RuntimeError("GPIO interrupt setup failed") from e

    def _on_zero_crossing(self, channel):
        """Handle zero-crossing event."""
        logging.info(f"Zero Crossing Detected on Pin {channel}")

    def _on_interrupt_request(self, channel):
        """Handle interrupt request event."""
        logging.info(f"Interrupt Request Detected on Pin {channel}")

    def close(self):
        """Close the SPI connection and reset GPIO pins."""
        try:
            self.spi.close()
            logging.info("SPI connection closed.")
            GPIO.cleanup()
            logging.info("GPIO cleanup done.")
        except Exception as e:
            logging.error("Error closing SPI connection or GPIO cleanup: %s", e)
            raise RuntimeError("Failed to close SPI connection or GPIO cleanup") from e

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
        register_address = self.REGISTERS[register_name]
        try:
            cmd = [0x80 | (register_address >> 8), register_address & 0xFF, 0x00, 0x00]
            logging.debug("Sending command to read register: %s", cmd)
            
            response = self._spi_transfer(cmd)
            if len(response) != 4:
                raise ValueError("Unexpected response length")
            value = (response[2] << 8) | response[3]
            
            logging.debug("Read register 0x%04X: 0x%04X", register_address, value)
            return value
            
        except Exception as e:
            logging.error("Error reading register 0x%04X: %s", register_address, e)
            raise RuntimeError(f"Failed to read register 0x{register_address:04X}") from e

    def _write_register(self, register_name, value):
        """Write data to a register."""
        
        if register_name not in self.REGISTERS:
            raise ValueError(f"Unknown register: {register_name}")
        register_address = self.REGISTERS[register_name]
        
        try:
            cmd = [register_address >> 8, register_address & 0xFF, value >> 8, value & 0xFF]
            self._spi_transfer(cmd)
            logging.debug("Wrote 0x%04X to register 0x%04X", value, register_address)
        except Exception as e:
            logging.error("Error writing to register 0x%04X: %s", register_address, e)
            raise RuntimeError(f"Failed to write to register 0x{register_address:04X}") from e
            
            
    def _read_scaled_value(self, register_name, scale):
        """Read a scaled value from a register."""
        try:
            raw_value = self._read_register(register_name)
            print(register_name," : ", raw_value ,"\n","Scale :",scale)
            return raw_value * scale
        except Exception as e:
            logging.error("Failed to read %s: %s", register_name, e)
            return None            

    def read_voltage(self, phase):
        """Read RMS Voltage."""
        try:
            register = f"Voltage{phase}"
            voltage = self._read_scaled_value(register, 0.01)
            logging.info("Voltage: %.2f V", voltage)
            return voltage
        except Exception as e:
            logging.error("Error reading voltage: %s", e)
            raise

    def read_current(self, phase):
        """Read RMS Current."""
        try:
            register = f"Current{phase}"
            current = self._read_scaled_value(register, 0.001)
            logging.info("Current: %.3f A", current)
            return current
        except Exception as e:
            logging.error("Error reading current: %s", e)
            raise

    def read_power(self, phase):
        """Read Active Power."""
        try:
            register = f"Power{phase}"
            power = self._read_scaled_value(register, 0.00032)
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
            self._write_register(self.REG_RESET_ENERGY, 0x0000)
            logging.info("Energy accumulator reset")
        except Exception as e:
            logging.error("Error resetting energy: %s", e)
            raise

    def check_status_flags(self):
        """Check status flags."""
        try:
            flags = self._read_register(self.REG_STATUS_FLAGS)
            logging.info("Status Flags: 0x%04X", flags)
            return flags
        except Exception as e:
            logging.error("Error checking status flags: %s", e)
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

    def read_phase_angle(self, phase):
        """Read Phase Angle."""
        try:
            register = f"PhaseAngle{phase}"
            phase_angle = self._read_scaled_value(register, 0.01)
            logging.info("Phase Angle: %.2f degrees", phase_angle)
            return phase_angle
        except Exception as e:
            logging.error("Error reading phase angle: %s", e)
            raise

    def read_frequency(self):
        """Read Frequency."""
        return self._read_scaled_value('Frequency', 0.01)

    def calibrate_voltage(self, calibration_value=None):
        """Calibrate Voltage Measurement."""
        try:
            calibration_value = calibration_value or self.DEFAULT_VOLTAGE_CAL
            self._write_register(self.REGISTERS['REG_VOLTAGE_CAL'], calibration_value)
            logging.info("Voltage calibrated with value 0x%04X", calibration_value)
        except Exception as e:
            logging.error("Error calibrating voltage: %s", e)
            raise

    def calibrate_current(self, calibration_value=None):
        """Calibrate Current Measurement."""
        try:
            calibration_value = calibration_value or self.DEFAULT_CURRENT_CAL
            self._write_register(self.REGISTERS["REG_CURRENT_CAL"], calibration_value)
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
        voltage = meter.read_voltage("A")
        current = meter.read_current("A")
        power = meter.read_power("A")
        #energy = meter.read_energy()
        #power_factor = meter.read_power_factor()
        phase_angle = meter.read_phase_angle("A")

        print(f"Voltage: {voltage} V")
        print(f"Current: {current} A")
        print(f"Power: {power} W")
        #print(f"Energy: {energy} kWh")
        #print(f"Power Factor: {power_factor}")
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
