import subprocess
import time
#from bluetooth_gatt_driver import BluetoothGattServer

def setup_bluetooth():
    """
    Automates the Bluetooth initialization process using `bluetoothctl`.
    """
    commands = [
        "power on",
        "pairable on",
        "discoverable on",
        "exit"
    ]
    
    try:
        # Open `bluetoothctl` as a subprocess
        process = subprocess.Popen(["bluetoothctl"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        for cmd in commands:
            process.stdin.write(cmd + "\n")
            process.stdin.flush()
            time.sleep(1)  # Allow the command to execute
        
        # Wait for completion
        process.stdin.close()
        process.wait()
        print("Bluetooth setup completed successfully.")
    
    except Exception as e:
        print(f"Error during Bluetooth setup: {e}")

def main():
    """
    Entry point for automating the BLE GATT server.
    """
    # Step 1: Setup Bluetooth
    setup_bluetooth()
    
    # Step 2: Start the GATT server
    #server = BluetoothGattServer()
    #server.run()

if __name__ == "__main__":
    main()
