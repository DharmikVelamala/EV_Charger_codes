import subprocess

class WifiManager:
    def modprobe_wifi(self, module_name="moal", config_file="nxp/wifi_mod_para.conf"):
        """Load Wi-Fi module using modprobe."""
        try:
            subprocess.run(['modprobe', module_name, f'mod_para={config_file}'], check=True)
            print(f"Module {module_name} loaded with config {config_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error loading module: {e}")
            return False
        return True

    def enable_wifi(self):
        """Enable Wi-Fi using connmanctl."""
        try:
            subprocess.run(['connmanctl', 'enable', 'wifi'], check=True)
            print("Wi-Fi enabled")
        except subprocess.CalledProcessError as e:
            print(f"Error enabling Wi-Fi: {e}")
            return False
        return True

    def scan_wifi(self):
        """Scan for available Wi-Fi networks."""
        try:
            subprocess.run(['connmanctl', 'scan', 'wifi'], check=True)
            print("Scanning for Wi-Fi networks...")
        except subprocess.CalledProcessError as e:
            print(f"Error scanning for networks: {e}")
            return False
        return True

    def list_services(self,ssid):
        """List available Wi-Fi services."""
        try:
            result = subprocess.run(['connmanctl', 'services'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            services = result.stdout.decode('utf-8').strip().split("\n")
            print("Available services:")
            for service in services:
                print(service)
                my_list = service.split(" ")
                SSID = [item for item in my_list if item]
                if SSID[-2]==ssid:
                    print(SSID)
                    return services,SSID
        except subprocess.CalledProcessError as e:
            print(f"Error listing services: {e}")
            return []

    '''def connect_to_network(self, service_name, passphrase):
        """Connect to a specific Wi-Fi network."""
        try:
            subprocess.run(['connmanctl', 'agent', 'on'], check=True)
            subprocess.run(['connmanctl', 'connect', service_name], input=f"Passphrase = {passphrase}\n", text=True, check=True)
            print(f"Connected to {service_name}")
            subprocess.run(['connmanctl', 'quit'])
        except subprocess.CalledProcessError as e:
            print(f"Error connecting to {service_name}: {e}")
            return False
        return True'''
        
    def connect_to_network(self, service_name, passphrase,SSID):
        """Connect to a specific Wi-Fi network."""
        try:
            # Start the connmanctl process
            process = subprocess.Popen(['connmanctl'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
            # Send the 'agent on' command to enable the agent
            process.stdin.write('agent on\n')
            process.stdin.flush()
    
            # Send the 'connect' command with the service name
            process.stdin.write(f'connect {service_name}\n')
            process.stdin.flush()

            if(SSID[-3]):
                process.stdin.write('yes\n')  # Respond to retry if prompted
                process.stdin.flush()
                process.stdin.write('quit\n')
                process.stdin.flush()
    
                # Wait for the process to complete
                stdout, stderr = process.communicate()
                print(stdout)
                if "Connected" in stdout:
                    print(f"Successfully connected to {service_name}")
                    return True
                else:
                    print(f"Failed to connect to {service_name}.")
                    print(stderr)
                    return False

    
            # Send the passphrase
            process.stdin.write(f"{passphrase}\n")
            process.stdin.flush()
    
            # Exit the connmanctl shell
            process.stdin.write('quit\n')
            process.stdin.flush()
    
            # Wait for the process to complete    
            stdout, stderr = process.communicate()
            print(stdout)
            if "Connected" in stdout:
                print(f"Successfully connected to {service_name}")
                return True    
            else:
                print(f"Failed to connect to {service_name}.")
                print(stderr)
                return False
        except Exception as e:
            print(f"Error connecting to {service_name}: {e}")
            return False
    

    def connect_wifi(self, ssid, passphrase):
        """Complete Wi-Fi connection procedure."""
        if self.modprobe_wifi() and self.enable_wifi() and self.scan_wifi():
            services,SSID = self.list_services(ssid)
            #print(services,"/n")
            # Filter services to find the one that matches the SSID (e.g., 'PSTI')
            service_name = None
            #for service in services:
                #if ssid in service:
                    # If 'PSTI' is found, use the service identifier (e.g., 'wifi_a841f4f2c841_50535449_managed_psk')
                    #service_name = service.strip().split(' ')[1]  # Extracting service name from the line
                    #break
            service_name = SSID[-1]
            if service_name:
                return self.connect_to_network(service_name, passphrase,SSID)
            else:
                print(f"Network with SSID '{ssid}' not found in available services.")
                return False
        return False

# Example Usage
wifi_manager = WifiManager()
result = wifi_manager.connect_wifi(ssid="PSTI", passphrase="psti@123")
print(f"Connection result: {result}")