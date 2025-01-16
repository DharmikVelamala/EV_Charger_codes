import smbus2
import time
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class BMP280:
    def __init__(self, bus=1, address=0x76):
        self.bus = smbus2.SMBus(bus)
        self.address = address
        self.calibration_params = {}
        self.load_calibration_data()
        self.configure_sensor()

    def read_register(self, register, length=1):
        """Read bytes from a register."""
        return self.bus.read_i2c_block_data(self.address, register, length)

    def write_register(self, register, value):
        """Write a byte to a register."""
        self.bus.write_byte_data(self.address, register, value)

    def load_calibration_data(self):
        """Load calibration data from the sensor."""
        calib = self.read_register(0x88, 24)  # Read calibration registers
        self.calibration_params = {
            "dig_T1": calib[1] << 8 | calib[0],
            "dig_T2": self.to_signed(calib[3] << 8 | calib[2]),
            "dig_T3": self.to_signed(calib[5] << 8 | calib[4]),
            "dig_P1": calib[7] << 8 | calib[6],
            "dig_P2": self.to_signed(calib[9] << 8 | calib[8]),
            "dig_P3": self.to_signed(calib[11] << 8 | calib[10]),
            "dig_P4": self.to_signed(calib[13] << 8 | calib[12]),
            "dig_P5": self.to_signed(calib[15] << 8 | calib[14]),
            "dig_P6": self.to_signed(calib[17] << 8 | calib[16]),
            "dig_P7": self.to_signed(calib[19] << 8 | calib[18]),
            "dig_P8": self.to_signed(calib[21] << 8 | calib[20]),
            "dig_P9": self.to_signed(calib[23] << 8 | calib[22]),
        }
        logging.info("Calibration parameters loaded: %s", self.calibration_params)

    def configure_sensor(self):
        """Configure the BMP280 sensor."""
        self.write_register(0xF4, 0x27)  # Set ctrl_meas: Normal mode, osrs_t=1, osrs_p=1
        self.write_register(0xF5, 0xA0)  # Set config: t_sb=1000ms, filter=4

    def read_raw_data(self):
        """Read raw temperature and pressure data."""
        data = self.read_register(0xF7, 6)
        raw_pressure = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        raw_temperature = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        return raw_temperature, raw_pressure

    def compensate_temperature(self, adc_T):
        """Compensate raw temperature data."""
        params = self.calibration_params
        var1 = (((adc_T >> 3) - (params["dig_T1"] << 1)) * params["dig_T2"]) >> 11
        var2 = (((((adc_T >> 4) - params["dig_T1"]) * ((adc_T >> 4) - params["dig_T1"])) >> 12) * params["dig_T3"]) >> 14
        t_fine = var1 + var2
        temperature = (t_fine * 5 + 128) >> 8
        return temperature / 100.0, t_fine

    def compensate_pressure(self, adc_P, t_fine):
        """Compensate raw pressure data."""
        params = self.calibration_params
        var1 = t_fine - 128000
        var2 = var1 * var1 * params["dig_P6"]
        var2 = var2 + ((var1 * params["dig_P5"]) << 17)
        var2 = var2 + (params["dig_P4"] << 35)
        var1 = ((var1 * var1 * params["dig_P3"]) >> 8) + ((var1 * params["dig_P2"]) << 12)
        var1 = (((1 << 47) + var1) * params["dig_P1"]) >> 33
        if var1 == 0:
            return 0
        p = 1048576 - adc_P
        p = ((p << 31) - var2) * 3125 // var1
        var1 = (params["dig_P9"] * (p >> 13) * (p >> 13)) >> 25
        var2 = (params["dig_P8"] * p) >> 19
        pressure = ((p + var1 + var2) >> 8) + (params["dig_P7"] << 4)
        return pressure / 25600.0

    def read_temperature_and_pressure(self):
        """Read and compensate temperature and pressure."""
        adc_T, adc_P = self.read_raw_data()
        temperature, t_fine = self.compensate_temperature(adc_T)
        pressure = self.compensate_pressure(adc_P, t_fine)
        return temperature, pressure

    @staticmethod
    def to_signed(value):
        """Convert an unsigned value to signed."""
        return value - 0x10000 if value > 0x7FFF else value

    def close(self):
        """Close the I2C connection."""
        self.bus.close()


# Main for testing
if __name__ == "__main__":
    try:
        sensor = BMP280()
        temperature, pressure = sensor.read_temperature_and_pressure()
        print(f"Temperature: {temperature:.2f} Â°C")
        print(f"Pressure: {pressure:.2f} hPa")
    finally:
        sensor.close()

