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
        #if register_name not in self.REGISTERS:
            #raise ValueError(f"Unknown register: {register_name}")
        
        #reg_address = self.REGISTERS[register_name]
        reg_address = register_name
        cmd = [0x80 | (reg_address >> 8), reg_address & 0xFF, 0x00, 0x00]
        response = self._spi_transfer(cmd)
        
        #if len(response) != 4:
            #raise RuntimeError("Invalid response length")

        result = (response[2] << 8) | response[3]
        #logging.debug("Read register %s (0x%04X): 0x%04X", register_name, reg_address, result)
        return result

    # Reading specific parameters

    def _convert_signed_value(self, value, bits):
        if value & (1 << (bits - 1)):
            return value - (1 << bits)
        return value
    
    def calculate_active_power(self,high_word, low_word):
        """
        Calculate active power in watts from 32-bit register values.
        
        Args:
            high_word (int): High 16 bits of the 32-bit register value.
            low_word (int): Low 16 bits of the 32-bit register value.
        
        Returns:
            float: Active power in watts.
        """
        # Combine high and low words
        try:
            register_value = (high_word << 16) | low_word
            if register_value & 0x80000000:  # If MSB is 1
                register_value -= 1 << 32  # Convert to signed 32-bit value

            power = register_value * 0.00032
            return power
        except Exception as e:
            logging.error("Failed to calculate active power: %s", e)
            raise RuntimeError("Failed to calculate active power") from e

        return power
    
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


    import logging

    def read_voltage(self, phase=None):
        """Read voltage for the specified phase or all phases by default."""
        voltage_registers = {
            'A': 'VoltageA',
            'B': 'VoltageB',
            'C': 'VoltageC',
        }
        try:
            if phase is None:
                # Reading voltage for all phases
                voltages = {p: self._read_register(reg_name) * 0.01 for p, reg_name in voltage_registers.items()}
                return voltages
            elif phase.upper() in voltage_registers:
                # Reading voltage for a specific phase
                reg_name = voltage_registers[phase.upper()]
                return self._read_register(reg_name) * 0.01
            else:
                # Invalid phase provided
                raise ValueError(f"Invalid phase '{phase}'. Valid options are 'A', 'B', or 'C'.")
        except AttributeError as e:
            logging.error("Error reading voltage: invalid register or method not available - %s", e)
            raise RuntimeError("Failed to read voltage due to an internal error") from e
        except ValueError as e:
            logging.error("Invalid phase provided: %s", e)
            raise ValueError(f"Invalid phase '{phase}'. Valid options are 'A', 'B', or 'C'.") from e
        except Exception as e:
            logging.error("Unexpected error occurred while reading voltage: %s", e)
            raise RuntimeError("Failed to read voltage") from e


    def read_current(self, phase=None):
        """Read current for the specified phase or all phases by default."""
        current_registers = {
            'A': 'CurrentA',
            'B': 'CurrentB',
            'C': 'CurrentC',
        }
        try:
            if phase is None:
                # Reading current for all phases
                currents = {p: self._read_register(reg_name) * 0.001 for p, reg_name in current_registers.items()}
                return currents
            elif phase.upper() in current_registers:
                # Reading current for a specific phase
                reg_name = current_registers[phase.upper()]
                return self._read_register(reg_name) * 0.001
            else:
                raise ValueError("Invalid phase. Choose 'A', 'B', or 'C'.")
        except AttributeError as e:
            raise RuntimeError("Error reading current: invalid register or method not available") from e
        except ValueError as e:
            raise ValueError(f"Invalid phase: {phase}. Valid options are 'A', 'B', or 'C'.") from e
        except Exception as e:
            raise RuntimeError("An unexpected error occurred while reading the current") from e


    def read_power(self, phase=None):
        """Read power for the specified phase or all phases by default."""
        power_registers = {
            'A': ('ApH_PowerA', 'ApL_PowerA'),
            'B': ('ApH_PowerB', 'ApL_PowerB'),
            'C': ('ApH_PowerC', 'ApL_PowerC'),
        }
        try:
            if phase is None:
                # Reading power for all phases
                powers = {}
                for p, (high, low) in power_registers.items():
                    high_word = self._read_register(high)
                    low_word = self._read_register(low)
                    powers[p] = self.calculate_active_power(high_word, low_word)
                return powers
            elif phase.upper() in power_registers:
                # Reading power for a specific phase
                high, low = power_registers[phase.upper()]
                high_word = self._read_register(high)
                low_word = self._read_register(low)
                return self.calculate_active_power(high_word, low_word)
            else:
                raise ValueError("Invalid phase. Choose 'A', 'B', or 'C'.")
        except AttributeError as e:
            raise RuntimeError("Error reading power: invalid register or method not available") from e
        except ValueError as e:
            raise ValueError(f"Invalid phase: {phase}. Valid options are 'A', 'B', or 'C'.") from e
        except Exception as e:
            raise RuntimeError("An unexpected error occurred while reading the power") from e

        
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

    try:
        # Initialize ATM90E3x object
        meter = ATM90E3x()

        # Test Reading Volatages, Currents, Frequency, Phase Angles, and Power
        logging.info("Reading Voltage:")
        print(meter.read_voltage())

        logging.info("Reading Current:")
        print(meter.read_current())

        logging.info("Reading Frequency:")
        print(meter.read_frequency())

        logging.info("Reading Phase Angles:")
        print(meter.read_phase_angle('A'))
        print(meter.read_phase_angle('B'))
        print(meter.read_phase_angle('C'))

        logging.info("Reading Power:")
        print(meter.read_power())

    except Exception as e:
        logging.error("Error during testing: %s", e)
    finally:
        GPIO.cleanup()
    """    meter = ATM90E3x()
    try:
        registers = {
        "Total": {"high": 0xD0, "low": 0xE0},  # Replace with actual register values
        "PhaseA": {"high": 0xD1, "low": 0xE1},
        "PhaseB": {"high": 0xD2, "low": 0xE2},
        "PhaseC": {"high": 0xD3, "low": 0xE3},
        "Total_APP": {"high": 0xB0, "low": 0xC0},  # Replace with actual register values
        "PhaseA_APP": {"high": 0xB9, "low": 0xC9},
        "PhaseB_APP": {"high": 0xBA, "low": 0xCA},
        "PhaseC_APP": {"high": 0xBB, "low": 0xCB},
        }

        # Calculate active power
        for phase, values in registers.items():
            high_word = meter.read_register(values["high"])
            low_word = meter.read_register(values["low"])
            power = meter.calculate_active_power(high_word, low_word)
            print(f"{phase} Active Power: {power:.4f} W\n")
            
            
        for i,j in meter.REGISTERS.items():
            result=meter._read_register(i)
            print(f'{i} - {hex(j)} :  {result}  hex value = {hex(result)}')
         
    finally:
        meter.close()"""

if __name__ == "__main__":
    main()

