import time
import random
from datetime import datetime
import threading
import os

motor_state = "OFF"
run_program = True

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def generate_sensor_data():
    """Generate realistic sensor values."""
    return {
        "N": random.randint(80, 160),
        "P": random.randint(40, 120),
        "K": random.randint(50, 200),
        "moisture": random.randint(25, 85),
        "temperature": round(random.uniform(20, 34), 1),
        "ph": round(random.uniform(5.5, 7.8), 2)
    }

def timestamp():
    return datetime.now().strftime("%d/%b/%Y %H:%M:%S")

def print_log(endpoint, status=200):
    """Print logs that look exactly like real Flask server output."""
    print(f'127.0.0.1 - - [{timestamp()}] "GET {endpoint} HTTP/1.1" {status} -')

def display_dashboard():
    global motor_state, run_program

    while run_program:
        data = generate_sensor_data()
        clear_screen()

        print("==============================================")
        print("     IoT SOIL & WATER MONITORING BACKEND      ")
        print("==============================================\n")

        print(f" Nitrogen (N):          {data['N']} mg/kg")
        print(f" Phosphorus (P):        {data['P']} mg/kg")
        print(f" Potassium (K):         {data['K']} mg/kg")
        print(f" Soil Moisture:         {data['moisture']} %")
        print(f" Temperature:           {data['temperature']} °C")
        print(f" Soil pH Level:         {data['ph']}")
        print(f" Motor Status:          {motor_state}\n")

        print("------------ SERVER LOGS -------------")
        print_log("/")
        print_log("/api/latest_reading")
        print_log("/api/sensor_history")
        print_log("/favicon.ico", status=404)
        print("-------------------------------------\n")

        print("Commands: on | off | exit")

        time.sleep(3)

def command_listener():
    global motor_state, run_program

    while run_program:
        cmd = input("> ").strip().lower()

        if cmd == "on":
            motor_state = "ON"
            print("✔ Motor turned ON")
        elif cmd == "off":
            motor_state = "OFF"
            print("✔ Motor turned OFF")
        elif cmd == "exit":
            print("🛑 Stopping server simulation...")
            run_program = False
        else:
            print("❌ Invalid command (use: on, off, exit)")

# ----------------- MAIN -----------------
if __name__ == "__main__":
    thread = threading.Thread(target=display_dashboard)
    thread.daemon = True
    thread.start()

    command_listener()
