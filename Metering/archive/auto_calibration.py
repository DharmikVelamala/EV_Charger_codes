import spidev
import time
import logging
import RPi.GPIO as GPIO
from registers import *
import math
# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Pin Definitions for GPIO
PINS = {
    'RST': 25,  # Reset Pin
    'CS': 8,    # Chip Select
}

class ATM90E3x:
    # Register Addresses for All Phases (from datasheet)
    REGISTERS = {
        'VoltageA':0xD9,
        'VoltageB': 0xDA,
        'VoltageC': 0xDB,
        'CurrentA': 0xDD,
        'CurrentB': 0xDE,
        'CurrentC': 0xDF,
        'PowerA': 0xB9,
        'PowerB': 0xBA,
        'PowerC': 0xBB,
        'Frequency': 0xB8,
        'PhaseAngleA': 0xF9,
        'PhaseAngleB': 0xFA,
        'PhaseAngleC': 0xFB,
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
    }

    DEFAULT_SPI_BUS = 0
    DEFAULT_SPI_DEVICE = 0
    DEFAULT_SPEED_HZ = 2000000

    def __init__(self, spi_bus=DEFAULT_SPI_BUS, spi_device=DEFAULT_SPI_DEVICE, speed_hz=DEFAULT_SPEED_HZ,linefreq=0x0087, pgagain=0x002A, ugain=0xc600, igainA=0x9D6B, igainB=0x9D60
    , igainC=0x8000):
        """Initialize the SPI connection and GPIO pin assignments."""
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        self.speed_hz = speed_hz
        self._linefreq = linefreq
        self._pgagain = pgagain
        self._ugain = ugain
        self._igainA = igainA
        self._igainB = igainB
        self._igainC = igainC


        
        '''"""Initialize the SPI connection and GPIO pin assignments."""
        self.spi_bus = spi_bus
        self.spi_device = spi_device
        self.speed_hz = speed_hz'''

        try:
            self.spi = spidev.SpiDev()
            self.spi.open(spi_bus, spi_device)
            self.spi.max_speed_hz = speed_hz
            self.spi.mode = 0b00  # SPI Mode 0
            logging.info("ATM90E3x initialized with SPI bus %d, device %d, speed %d Hz", spi_bus, spi_device, speed_hz)

            self._init_gpio()
            self.reset_device()
            self._init_config()
            #self._init_gpio()
            #self.reset_device()
            
            time.sleep(5)
            #self._write_register(FreqLoTh, 0x0012)
        except Exception as e:
            logging.error("Initialization failed: %s", e)
            raise RuntimeError("Initialization failed") from e

    def _init_gpio(self):
        
        """Initialize GPIO pins for the ATM90E3x."""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PINS['RST'], GPIO.OUT)
        GPIO.output(PINS['RST'], GPIO.HIGH)  # Set reset pin high initially
        logging.info("GPIO initialized.")

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
            
    def _round_number(self, f_num):
        if f_num - math.floor(f_num) < 0.5:
            return math.floor(f_num)
        return math.ceil(f_num)
    
    def _init_config(self):
        # CurrentGainCT2 = 25498  #25498 - SCT-013-000 100A/50mA
        if (self._linefreq == 4485 or self._linefreq == 5231):
            # North America power frequency
            FreqHiThresh = 61 * 100
            FreqLoThresh = 59 * 100
            sagV = 90
        if (self._linefreq == 0x0087):
            sagV=70

        else:
            FreqHiThresh = 51 * 100
            FreqLoThresh = 49 * 100
            sagV = 190
            

        # calculation for voltage sag threshold - assumes we do not want to go under 90v for split phase and 190v otherwise
        # sqrt(2) = 1.41421356
        fvSagTh = (sagV * 100 * 1.41421356) / (2 * self._ugain / 32768)
        # convert to int for sending to the atm90e32.
        vSagTh = self._round_number(fvSagTh)

        self._write_register(SoftReset, 0x789A)   # Perform soft reset
        # enable register config access
        self._write_register( CfgRegAccEn, 0x55AA)
        self._write_register( MeterEn, 0x0001)   # Enable Metering

        #self._write_register( SagTh, vSagTh)         # Voltage sag threshold
        # High frequency threshold - 61.00Hz
        #self._write_register( FreqHiTh, FreqHiThresh)
        # Lo frequency threshold - 59.00Hz
        #self._write_register( FreqLoTh, FreqLoThresh)
        self._write_register( EMMIntEn0, 0xB76F)   # Enable interrupts
        self._write_register( EMMIntEn1, 0xDDFD)   # Enable interrupts
        self._write_register( EMMIntState0, 0x0001)  # Clear interrupt flags
        self._write_register( EMMIntState1, 0x0001)  # Clear interrupt flags
        # ZX2, ZX1, ZX0 pin config
        self._write_register( ZXConfig, 0x0A55)

        # Set metering config values (CONFIG)
        # PL Constant MSB (default) - Meter Constant = 3200 - PL Constant = 140625000
        self._write_register( PLconstH, 0x0861)
        # PL Constant LSB (default) - this is 4C68 in the application note, which is incorrect
        self._write_register( PLconstL, 0xC468)
        # Mode Config (frequency set in main program)
        self._write_register( MMode0, self._linefreq)
        # PGA Gain Configuration for Current Channels - 0x002A (x4) # 0x0015 (x2) # 0x0000 (1x)
        self._write_register( MMode1, self._pgagain)
        # Active Startup Power Threshold - 50% of startup current = 0.9/0.00032 = 2812.5
        self._write_register( PStartTh, 0x0AFC)
        # Reactive Startup Power Threshold
        self._write_register( QStartTh, 0x0AEC)
        # Apparent Startup Power Threshold
        self._write_register( SStartTh, 0x0000)
        # Active Phase Threshold = 10% of startup current = 0.06/0.00032 = 187.5
        self._write_register( PPhaseTh, 0x00BC)
        self._write_register( QPhaseTh, 0x0000)    # Reactive Phase Threshold
        # Apparent  Phase Threshold
        self._write_register( SPhaseTh, 0x0000)

        # Set metering calibration values (CALIBRATION)
        self._write_register( PQGainA, 0x0000)     # Line calibration gain
        self._write_register( PhiA, 0x0000)        # Line calibration angle
        self._write_register( PQGainB, 0x0000)     # Line calibration gain
        self._write_register( PhiB, 0x0000)        # Line calibration angle
        self._write_register( PQGainC, 0x0000)     # Line calibration gain
        self._write_register( PhiC, 0x0000)        # Line calibration angle
        # A line active power offset
        self._write_register( PoffsetA, 0x0000)
        # A line reactive power offset
        self._write_register( QoffsetA, 0x0000)
        # B line active power offset
        self._write_register( PoffsetB, 0x0000)
        # B line reactive power offset
        self._write_register( QoffsetB, 0x0000)
        # C line active power offset
        self._write_register( PoffsetC, 0x0000)
        # C line reactive power offset
        self._write_register( QoffsetC, 0x0000)

        # Set metering calibration values (HARMONIC)
        # A Fund. active power offset
        self._write_register( POffsetAF, 0x0000)
        # B Fund. active power offset
        self._write_register( POffsetBF, 0x0000)
        # C Fund. active power offset
        self._write_register( POffsetCF, 0x0000)
        # A Fund. active power gain
        self._write_register( PGainAF, 0x0000)
        # B Fund. active power gain
        self._write_register( PGainBF, 0x0000)
        # C Fund. active power gain
        self._write_register( PGainCF, 0x0000)

        # Set measurement calibration values (ADJUST)
        self._write_register( UgainA, self._ugain)      # A Voltage rms gain
        # A line current gain
        self._write_register( IgainA, self._igainA)
        self._write_register( UoffsetA, 0x0000)    # A Voltage offset
        self._write_register( IoffsetA, 0x0000)    # A line current offset
        self._write_register( UgainB, self._ugain)      # B Voltage rms gain
        # B line current gain
        self._write_register( IgainB, self._igainB)
        self._write_register( UoffsetB, 0x0000)    # B Voltage offset
        self._write_register( IoffsetB, 0x0000)    # B line current offset
        self._write_register( UgainC, self._ugain)      # C Voltage rms gain
        # C line current gain
        self._write_register( IgainC, self._igainC)
        self._write_register( UoffsetC, 0x0000)    # C Voltage offset
        self._write_register( IoffsetC, 0xFFFF)    # C line current offset

        self._write_register( CfgRegAccEn, 0x0000)  # end configuration

    def _spi_transfer(self, data):
        """Perform an SPI transfer."""
        try:
            
           #logging.debug("Sending SPI data: %s", data)
            response = self.spi.xfer2(data)
            #logging.debug("SPI transfer: Sent %s, Received %s", data, response)
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
        #logging.debug("Read register %s (0x%04X): 0x%04X", register_name, reg_address, result)
        return result

    def _write_register(self, register_name, value):
        """Write data to a register."""
        #if register_name not in self.REGISTERS:
         #   raise ValueError(f"Unknown register: {register_name}")
        
        #reg_address = self.REGISTERS[register_name]
        reg_address = register_name
        cmd = [reg_address >> 8, reg_address & 0xFF, value >> 8, value & 0xFF]
        self._spi_transfer(cmd)
        logging.debug("Wrote 0x%04X to register %s (0x%04X)", value, hex(register_name), reg_address)
        
    def read_register(self, reg_addr):
        """Read data from a register."""
        high_byte = (reg_addr >> 8) & 0xFF
        low_byte = reg_addr & 0xFF
        cmd = [high_byte | 0x80, low_byte, 0x00, 0x00]
        response = self.spi.xfer2(cmd)
        return (response[2] << 8) | response[3]
        
    def calibrate_power_offsets(self, phase, measured_value):
        """
        Calibrate power offsets for a specific phase.
        Args:
            phase (str): 'A', 'B', or 'C'
            measured_value (int): Current power value under no-load conditions
        """
        offset_registers = {'A': 0x51, 'B': 0x52, 'C': 0x53}
        if phase in offset_registers:
            current_offset = self.read_register(offset_registers[phase])
            new_offset = current_offset - measured_value
            self._write_register(offset_registers[phase], new_offset)
        
    def calibrate_power_gain(self, phase, actual_power, measured_power):
        """
        Calibrate power gain for a specific phase.
        Args:
            phase (str): 'A', 'B', or 'C'
            actual_power (float): Actual power in watts measured with a trusted meter
            measured_power (float): Power measured by the ATM90E3x
        """
        gain_registers = {'A': 0x54, 'B': 0x55, 'C': 0x56}
        if phase in gain_registers:
            current_gain = self.read_register(gain_registers[phase])
            new_gain = int(current_gain * (actual_power / measured_power))
            self._write_register(gain_registers[phase], new_gain)

    def read_fundamental_active_power(self):
        """Read the fundamental active power for all phases."""
        power_a = self.read_register(0x31)  # Phase A Active Power
        power_b = self.read_register(0x32)  # Phase B Active Power
        power_c = self.read_register(0x33)  # Phase C Active Power
        return {
            'Phase A': power_a,
            'Phase B': power_b,
            'Phase C': power_c
        }

    def full_calibration(self, phase, actual_power):
        """
        Perform a full calibration for the specified phase.
        Args:
            phase (str): 'A', 'B', or 'C'
            actual_power (float): Known load in watts for calibration
        """
        # Step 1: Measure power without load and calibrate offset
        #no_load_power = self.read_register(0x31 if phase == 'A' else 0x32 if phase == 'B' else 0x33)
        #self.calibrate_power_offsets(phase, no_load_power)
        
        # Step 2: Measure power with a known load and calibrate gain
        measured_power = self.read_register(0x31 if phase == 'A' else 0x32 if phase == 'B' else 0x33)
        print(measured_power)
        self.calibrate_power_gain(phase, actual_power, measured_power)

        
    

# Example Usage
def main():
    try:
        meter = ATM90E3x()
        for i,j in meter.REGISTERS.items():  # Loop through all possible register addresses
            try:
                result = meter._read_register(i)
                print(f"Register : {hex(j)} - {i} : {hex(result)} decimal value:{result}")
        #meter.full_calibration('A', actual_power=100.0)  # 100W load for Phase A
        #meter.full_calibration('B', actual_power=2000.0)  # 150W load for Phase B
        #meter.full_calibration('C', actual_power=240.0)  # 200W load for Phase C
            except Exception as e:
                print(f"Error reading register {hex(i)}: {e}")
    except Exception as e:
        logging.error("Failed to initialize the ATM90E3x: %s", e)

if __name__ == "__main__":
    main()

