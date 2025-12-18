import serial
import requests
import time
import json

# =================================================================
# 1. CONFIGURATION - UPDATE THESE VALUES
# =================================================================
SERIAL_PORT = 'COM5'  # Change to your Arduino port (e.g., COM3, /dev/ttyUSB0)
BAUD_RATE = 9600
SERVER_URL = 'http://127.0.0.1:5000'

# =================================================================
# 2. BRIDGE SCRIPT LOGIC
# =================================================================
def connect_to_arduino():
    """Attempts to connect to the Arduino, returns the serial object or None."""
    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"✅ Successfully connected to Arduino on {SERIAL_PORT}")
        time.sleep(2)  # Wait for Arduino to reset
        return arduino
    except serial.SerialException as e:
        print(f"❌ Error: Could not connect to {SERIAL_PORT}. Is it plugged in and is the port correct?")
        print(f"   Details: {e}")
        return None

def run_bridge():
    print("=" * 60)
    print("🌊 Arduino to Web Dashboard Bridge (Updated)")
    print("=" * 60)
    
    arduino = connect_to_arduino()
    last_motor_command = False  # We now use a boolean (True/False)
    last_status_check = time.time()

    while True:
        if not arduino or not arduino.is_open:
            print("\n⚠️  Arduino disconnected. Attempting to reconnect in 5 seconds...")
            time.sleep(5)
            arduino = connect_to_arduino()
            continue

        try:
            # --- This part for reading from Arduino and printing is fine ---
            if arduino.in_waiting > 0:
                line = arduino.readline().decode('utf-8').strip()
                if line:
                    print(f"ℹ️  Arduino: {line}")

            # --- 2. CHECK SERVER FOR MOTOR COMMANDS (every 1 second) ---
            current_time = time.time()
            if current_time - last_status_check >= 1.0:
                last_status_check = current_time
                
                try:
                    # ** CHANGE 1: The endpoint is the same, but the JSON response is different. **
                    response = requests.get(f"{SERVER_URL}/api/motor_status", timeout=3)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # ** CHANGE 2: We now check the 'motor_on' boolean key, not the 'status' string. **
                        is_motor_on = data.get('motor_on', False)
                        
                        # Only send command if the state has changed
                        if is_motor_on != last_motor_command:
                            # The command sent to Arduino remains the same (MOTOR_ON/MOTOR_OFF)
                            command_str = "ON" if is_motor_on else "OFF"
                            command_to_send = f"MOTOR_{command_str}\n"
                            
                            arduino.write(command_to_send.encode())
                            print(f"🔧 Sent to Arduino: {command_to_send.strip()}")
                            last_motor_command = is_motor_on
                            
                except requests.exceptions.RequestException:
                    pass # Silently ignore if server is temporarily unavailable

        except serial.SerialException as e:
            print(f"🚨 Arduino communication error: {e}")
            if arduino and arduino.is_open:
                arduino.close()
            arduino = None
            continue
            
        except KeyboardInterrupt:
            print("\n" + "=" * 60)
            print("🛑 Bridge stopped by user")
            print("=" * 60)
            if arduino and arduino.is_open:
                arduino.close()
            break
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        time.sleep(0.1)

if __name__ == '__main__':
    run_bridge()