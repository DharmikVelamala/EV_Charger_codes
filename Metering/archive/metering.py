import spidev
import time
import logging
import RPi.GPIO as GPIO

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Pin Definitions for GPIO
PINS = {
    'RST': 25,  # Reset Pin
    'SDI': 10,  # SPI Data In
    'SDO': 9,   # SPI Data Out
    'CS': 8,    # Chip Select
    'SCLK': 11  # SPI Clock
}

class ATM90E3x:
    # Register Addresses (from datasheet)
    REGISTERS = {
        'VoltageA':0xD9,
        'VoltageB': 0xDA,
        'VoltageC': 0xDB,
        'CurrentA': 0xDD,
        'CurrentB': 0xDE,
        'CurrentC': 0xDF,
        'ApH_PowerA': 0xB9,
        'ApH_PowerB': 0xBA,
        'ApH_PowerC': 0xBB,
        'ApL_PowerA': 0xC9,
        'ApL_PowerB': 0xCA,
        'ApL_PowerC': 0xCB,
        'AH_PowerA': 0xD1,
        'AH_PowerB': 0xD2,
        'AH_PowerC': 0xD3,
        'AL_Power_A': 0xE1,
        'AL_Power_B': 0xE2,
        'AL_Power_C': 0xE3,
        'Frequency': 0xF8,
        'PhaseAngleA': 0xFD,
        'PhaseAngleB': 0xFE,
        'PhaseAngleC': 0xFF,
        'Ugain_A':0x61,
        'Igain_A':0x62,
        'U_offset_A':0x63,
        'I_offset_A':0x64,
        'Ugain_B':0x65,
        'Igain_B':0x66,
        'U_offset_B':0x67,
        'I_offset_B':0x68,
        'Ugain_C':0x69,
        'Igain_C':0x6A,
        'U_offset_C':0x6B,
        'I_offset_C':0x6C,
        'POFFset_A': 0x51,
        'POFFset_B': 0x52,
        'POFFset_C': 0x53,
        'Power_gain_A': 0x54,
        'Power_gain_B': 0x55,
        'Power_gain_C': 0x56,
    }

    DEFAULT_SPI_BUS = 0
    DEFAULT_SPI_DEVICE = 0
    DEFAULT_SPEED_HZ = 200000

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
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(PINS['RST'], GPIO.OUT)
            GPIO.output(PINS['RST'], GPIO.HIGH)  # Set reset pin high initially
            logging.info("GPIO initialized.")
        except Exception as e:
            logging.error("Failed to initialize GPIO: %s", e)
            raise RuntimeError("GPIO initialization failed") from e

    def reset_device(self):
        """Reset the ATM90E3x device."""
        try:
            GPIO.output(PINS['RST'], GPIO.LOW)
            time.sleep(0.1)  # Hold reset for 100ms
            GPIO.output(PINS['RST'], GPIO.HIGH)
            time.sleep(0.1)  # Allow the device to stabilize
            logging.info("Device reset complete.")
        except Exception as e:
            logging.error("Failed to reset device: %s", e)
            raise RuntimeError("Device reset failed") from e

    def _spi_transfer(self, data):
        """Perform an SPI transfer."""
        try:
            response = self.spi.xfer2(data)
            return response
        except Exception as e:
            logging.error("SPI transfer failed: %s", e)
            raise RuntimeError("SPI transfer failed") from e

    def _read_register(self, register_name):
        """Read data from a register."""
        try:
            if register_name not in self.REGISTERS:
                raise ValueError(f"Unknown register: {register_name}")
            
            reg_address = self.REGISTERS[register_name]
            cmd = [0x80 | (reg_address >> 8), reg_address & 0xFF, 0x00, 0x00]
            response = self._spi_transfer(cmd)
            
            result = (response[2] << 8) | response[3]
            return result
        except Exception as e:
            logging.error("Failed to read register %s: %s", register_name, e)
            raise RuntimeError(f"Failed to read register {register_name}") from e

    def _write_register(self, register_name, value):
        """Write data to a register."""
        try:
            if register_name not in self.REGISTERS:
                raise ValueError(f"Unknown register: {register_name}")
            
            reg_address = self.REGISTERS[register_name]
            cmd = [reg_address >> 8, reg_address & 0xFF, value >> 8, value & 0xFF]
            self._spi_transfer(cmd)
            logging.debug("Wrote 0x%04X to register %s (0x%04X)", value, register_name, reg_address)
        except Exception as e:
            logging.error("Failed to write register %s: %s", register_name, e)
            raise RuntimeError(f"Failed to write register {register_name}") from e

    def read_register(self, register_name):
        """Read data from a register."""
        try:
            reg_address = register_name
            cmd = [0x80 | (reg_address >> 8), reg_address & 0xFF, 0x00, 0x00]
            response = self._spi_transfer(cmd)
            
            result = (response[2] << 8) | response[3]
            return result
        except Exception as e:
            logging.error("Failed to read register %s: %s", register_name, e)
            raise RuntimeError(f"Failed to read register {register_name}") from e

    def calculate_active_power(self, high_word, low_word):
        """Calculate active power in watts from 32-bit register values."""
        try:
            register_value = (high_word << 16) | low_word
            if register_value & 0x80000000:  # If MSB is 1
                register_value -= 1 << 32  # Convert to signed 32-bit value

            power = register_value * 0.00032
            return power
        except Exception as e:
            logging.error("Failed to calculate active power: %s", e)
            raise RuntimeError("Failed to calculate active power") from e

    def read_frequency(self):
        """Read frequency in Hz."""
        try:
            raw_value = self._read_register('Frequency')
            return raw_value * 0.01
        except Exception as e:
            logging.error("Failed to read frequency: %s", e)
            raise RuntimeError("Failed to read frequency") from e

    def read_phase_angle(self, phase):
        """Read phase angle for the specified phase."""
        try:
            phase_registers = {'A': 'PhaseAngleA', 'B': 'PhaseAngleB', 'C': 'PhaseAngleC'}
            if phase.upper() not in phase_registers:
                raise ValueError("Invalid phase. Choose 'A', 'B', or 'C'.")
            return self._read_register(phase_registers[phase.upper()]) * 0.1
        except Exception as e:
            logging.error("Failed to read phase angle for phase %s: %s", phase, e)
            raise RuntimeError(f"Failed to read phase angle for phase {phase}") from e

    def read_voltage(self, phase=None):
        """Read voltage for the specified phase or all phases by default."""
        try:
            voltage_registers = {
                'A': 'VoltageA',
                'B': 'VoltageB',
                'C': 'VoltageC',
            }
            if phase is None:
                voltages = {p: self._read_register(reg_name) * 0.01 for p, reg_name in voltage_registers.items()}
                return voltages
            elif phase.upper() in voltage_registers:
                reg_name = voltage_registers[phase.upper()]
                return self._read_register(reg_name) * 0.01
            else:
                raise ValueError("Invalid phase. Choose 'A', 'B', or 'C'.")
        except Exception as e:
            logging.error("Failed to read voltage: %s", e)
            raise RuntimeError("Failed to read voltage") from e
