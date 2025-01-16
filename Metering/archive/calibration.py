import spidev
import time

class ATM90E32AS:
    def __init__(self, spi_bus=0, spi_device=0, speed_hz=2000000):
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_device)
        self.spi.max_speed_hz = speed_hz
        self.spi.mode = 0b11

    def write_register(self, reg_addr, data):
        """Write data to a register."""
        high_byte = (reg_addr >> 8) & 0xFF
        low_byte = reg_addr & 0xFF
        data_high = (data >> 8) & 0xFF
        data_low = data & 0xFF
        cmd = [high_byte & 0x7F, low_byte, data_high, data_low]
        self.spi.xfer2(cmd)

    def read_register(self, reg_addr):
        """Read data from a register."""
        high_byte = (reg_addr >> 8) & 0xFF
        low_byte = reg_addr & 0xFF
        cmd = [high_byte | 0x80, low_byte, 0x00, 0x00]
        response = self.spi.xfer2(cmd)
        return (response[2] << 8) | response[3]

    def calibrate(self):
        """Perform calibration for the M90E32AS."""
        # Set PL_Constant (high and low parts)
        self.write_register(0x31, 0x0861)  # PLconstH
        self.write_register(0x32, 0xC468)  # PLconstL
        
        # Set metering mode configuration
        self.write_register(0x33, 0x0087)  # MMode0: Enable energy computations
        self.write_register(0x34, 0x0000)  # MMode1: Default PGA Gain
        
        # Set startup power thresholds
        self.write_register(0x35, 0x0000)  # PStartTh: Active power threshold
        self.write_register(0x36, 0x0000)  # QStartTh: Reactive power threshold
        self.write_register(0x37, 0x0000)  # SStartTh: Apparent power threshold
        
        # Set phase thresholds
        self.write_register(0x38, 0x0000)  # PPhaseTh
        self.write_register(0x39, 0x0000)  # QPhaseTh
        self.write_register(0x3A, 0x0000)  # SPhaseTh
        
        # Gain and phase compensation for each phase
        self.write_register(0x26, 0x0000)  # GainAIrms01
        self.write_register(0x27, 0x0000)  # GainAIrms2
        self.write_register(0x24, 0x0000)  # PhiAIrms01
        self.write_register(0x25, 0x0000)  # PhiAIrms2

        self.write_register(0x2A, 0x0000)  # GainBIrms01
        self.write_register(0x2B, 0x0000)  # GainBIrms2
        self.write_register(0x28, 0x0000)  # PhiBIrms01
        self.write_register(0x29, 0x0000)  # PhiBIrms2

        self.write_register(0x2E, 0x0000)  # GainCIrms01
        self.write_register(0x2F, 0x0000)  # GainCIrms2
        self.write_register(0x2C, 0x0000)  # PhiCIrms01
        self.write_register(0x2D, 0x0000)  # PhiCIrms2

        # Voltage gain temperature compensation
        self.write_register(0x1A, 0x0000)  # UGainTAB
        self.write_register(0x1B, 0x0000)  # UGainTC

        print("Calibration complete.")

# Example Usage
def main():
    meter = ATM90E32AS()
    meter.calibrate()
    print("Calibration routine executed successfully.")

if __name__ == "__main__":
    main()
