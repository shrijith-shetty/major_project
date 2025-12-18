from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import random
from datetime import datetime, timedelta
from serial.tools import list_ports
import math


import serial
import threading
import time





app = Flask(__name__)
CORS(app)

# ============================
# SERIAL PORT CONFIG
# SERIAL PORT CONFIG
NPK_PORT = "COM3"        # NPK Arduino (already working)
WATER_PORT = "COM3"      # ← change this to the real port
npk_ser = None
water_ser = None

BAUD_RATE = 9600


# ============================
# PUMP / TANK RUNTIME STATE
# ============================
current_pump_status = "OFF"   # "ON" when motor is running
current_flow_rate = 0.0       # L/min (simulated or from flow sensor)
session_total_volume = 0.0    # L used in current session
pump_session_start = None     # datetime when session started

# simple fallback tank model (will be overridden by ultrasonic if available)
water_tank_level_liters = 0.0
TANK_CAPACITY_LITERS = 0.0    # will be set based on bottle geometry



# ============================
# GLOBAL STATE VARIABLES
# ============================
# Live sensor state from Arduinos
latest_npk_reading = {
    "timestamp": None,
    "temp": None,
    "humidity": None,  # using as soil moisture %
    "ph": None,
    "n": None,
    "p": None,
    "k": None
}

latest_water_status = {
    "timestamp": None,
    "distance_cm": None,
    "pump_on": False
}

# ============================
# AUTO IRRIGATION CONFIG
# ============================
auto_mode_enabled = False            # default: manual control
auto_irrigation_active = False       # True only during 3s auto cycle
last_auto_irrigation_time = None     # last time auto cycle completed
AUTO_MOISTURE_THRESHOLD = 30.0       # % moisture below which soil is "dry"
AUTO_IRRIGATION_COOLDOWN_SEC = 30    # minimum gap between auto cycles


# ============================
# CROP MARKET INFO (Price in INR per Quintal)
# ============================
CROP_MARKET_INFO = {
    "paddy": {"price": 2200, "demand": "High"},
    "maize": {"price": 1850, "demand": "Medium"},
    "cotton": {"price": 6500, "demand": "Very High"},
    "wheat": {"price": 2400, "demand": "High"},
    "groundnut": {"price": 5500, "demand": "Medium"},
    "sugarcane": {"price": 300, "demand": "High"},
    "pulses": {"price": 8500, "demand": "Very High"},
    "millets": {"price": 2800, "demand": "Medium"}
}

# ============================
# FERTILIZER DATABASE
# ============================
FERTILIZER_INFO = {
    "Urea": "Primarily for Nitrogen deficiency. Apply in 2-3 splits during the vegetative stage for best results.",
    "DAP": "Ideal for correcting low Phosphorus. Apply as a basal dose at the time of sowing.",
    "MOP": "Best for Potassium deficiency, crucial during the reproductive and ripening stages for grain quality.",
    "10-26-26": "A balanced NPK fertilizer good for basal application when both P and K are moderately low.",
    "19-19-19": "A general-purpose balanced fertilizer suitable for maintenance when nutrient levels are adequate."
}

# ============================
# CROP GROWTH STAGE DATABASE WITH IMAGES
# ============================
CROP_DATA = {
    "paddy": {
        "name": "Paddy (Rice)",
        "main_image": "https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=800",
        "stages": [
            {'name': 'Nursery', 'startDay': 1, 'endDay': 30, 'water_liters_per_acre': 25000,
             'irrigation_frequency': 'Every 2 days', 'nutrient_needs': 'Low P for roots',
             'image': "https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=800",
             'note': 'Ensure good drainage to prevent seedling rot. A raised nursery bed is ideal.'},
            {'name': 'Vegetative', 'startDay': 31, 'endDay': 80, 'water_liters_per_acre': 200000,
             'irrigation_frequency': 'Maintain 2-5cm flood', 'nutrient_needs': 'High Nitrogen (N)',
             'image': "https://images.unsplash.com/photo-1536063211352-0c123ae0d991?w=800",
             'note': 'Maintain a shallow flood to control weeds and regulate soil temperature.'},
            {'name': 'Reproductive', 'startDay': 81, 'endDay': 110, 'water_liters_per_acre': 180000,
             'irrigation_frequency': 'Daily flooding', 'nutrient_needs': 'Potassium (K) & Phosphorus (P)',
             'image': "https://images.unsplash.com/photo-1571336672656-a6c1ce53a0d2?w=800",
             'note': 'Water stress at this stage can severely impact grain formation and yield.'},
            {'name': 'Ripening', 'startDay': 111, 'endDay': 140, 'water_liters_per_acre': 0,
             'irrigation_frequency': 'Stop Irrigation', 'nutrient_needs': 'Potassium (K) for quality',
             'image': "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=800",
             'note': 'Draining the field 10-15 days before harvest allows for uniform grain maturity.', 
             'yield_per_acre': 24}
        ]
    },
    "maize": {
        "name": "Maize (Corn)",
        "main_image": "https://images.unsplash.com/photo-1603048588665-791ca8aea617?w=800",
        "stages": [
            {'name': 'Emergence', 'startDay': 1, 'endDay': 10, 'water_liters_per_acre': 20000,
             'irrigation_frequency': 'Every 4-5 days', 'nutrient_needs': 'Starter P',
             'image': "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?w=800",
             'note': 'Ensure uniform soil moisture for even germination across the field.'},
            {'name': 'Vegetative', 'startDay': 11, 'endDay': 50, 'water_liters_per_acre': 45000,
             'irrigation_frequency': 'Weekly', 'nutrient_needs': 'High Nitrogen (N)',
             'image': "https://images.unsplash.com/photo-1603048588665-791ca8aea617?w=800",
             'note': 'Period of rapid growth. Apply nitrogen before predicted rainfall for best absorption.'},
            {'name': 'Tasseling & Silking', 'startDay': 51, 'endDay': 75, 'water_liters_per_acre': 60000,
             'irrigation_frequency': 'Every 5 days', 'nutrient_needs': 'Potassium (K)',
             'image': "https://images.unsplash.com/photo-1595855759917-5c1b10e5a876?w=800",
             'note': 'Water stress can lead to poor pollination and reduced kernel count.'},
            {'name': 'Grain Fill & Maturity', 'startDay': 76, 'endDay': 120, 'water_liters_per_acre': 30000,
             'irrigation_frequency': 'Every 10 days', 'nutrient_needs': 'Minimal',
             'image': "https://images.unsplash.com/photo-1603048588665-791ca8aea617?w=800",
             'note': 'Allow crop to dry down for optimal moisture content for storage.', 
             'yield_per_acre': 25}
        ]
    },
    "cotton": {
        "name": "Cotton",
        "main_image": "https://images.unsplash.com/photo-1565191999001-551c187427bb?w=800",
        "stages": [
            {'name': 'Germination', 'startDay': 1, 'endDay': 15, 'water_liters_per_acre': 18000,
             'irrigation_frequency': 'Every 5 days', 'nutrient_needs': 'Basal NPK',
             'image': "https://images.unsplash.com/photo-1615835513503-ed5661aba9c4?w=800",
             'note': 'Avoid crusting of the topsoil which can inhibit seedling emergence.'},
            {'name': 'Vegetative', 'startDay': 16, 'endDay': 60, 'water_liters_per_acre': 35000,
             'irrigation_frequency': 'Every 8-10 days', 'nutrient_needs': 'Nitrogen (N) top dress',
             'image': "https://images.unsplash.com/photo-1595856886611-0e1738b80f6e?w=800",
             'note': 'Monitor for pests like aphids and jassids during this leafy growth stage.'},
            {'name': 'Flowering & Boll Development', 'startDay': 61, 'endDay': 120, 'water_liters_per_acre': 50000,
             'irrigation_frequency': 'Weekly', 'nutrient_needs': 'High P & K',
             'image': "https://images.unsplash.com/photo-1565191999001-551c187427bb?w=800",
             'note': 'Inconsistent watering can lead to square and boll drop, reducing yield.'},
            {'name': 'Boll Opening & Maturation', 'startDay': 121, 'endDay': 160, 'water_liters_per_acre': 10000,
             'irrigation_frequency': 'Every 15 days', 'nutrient_needs': 'Foliar sprays if needed',
             'image': "https://images.unsplash.com/photo-1591631113945-2effc5c49159?w=800",
             'note': 'Use of a defoliant can help in uniform boll opening and makes picking easier.', 
             'yield_per_acre': 5}
        ]
    },
    "wheat": {
        "name": "Wheat",
        "main_image": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=800",
        "stages": [
            {'name': 'Crown Root Initiation (CRI)', 'startDay': 1, 'endDay': 25, 'water_liters_per_acre': 40000,
             'irrigation_frequency': 'At 21 days (Critical)', 'nutrient_needs': 'Basal NPK',
             'image': "https://images.unsplash.com/photo-1606854428728-5fe3eea23475?w=800",
             'note': 'The first irrigation at the CRI stage (21-25 days) is the most critical for wheat.'},
            {'name': 'Tillering', 'startDay': 26, 'endDay': 50, 'water_liters_per_acre': 35000,
             'irrigation_frequency': 'Every 20 days', 'nutrient_needs': 'Nitrogen (N) top dress',
             'image': "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=800",
             'note': 'Proper moisture encourages development of more tillers, leading to more heads.'},
            {'name': 'Flowering & Milking', 'startDay': 51, 'endDay': 90, 'water_liters_per_acre': 45000,
             'irrigation_frequency': 'Every 15 days', 'nutrient_needs': 'Second N top dress',
             'image': "https://images.unsplash.com/photo-1595856885888-afb0620f6e61?w=800",
             'note': 'High temperatures or water stress during flowering can harm grain development.'},
            {'name': 'Grain Filling & Maturing', 'startDay': 91, 'endDay': 120, 'water_liters_per_acre': 15000,
             'irrigation_frequency': 'Stop Irrigation', 'nutrient_needs': 'Potassium (K)',
             'image': "https://images.unsplash.com/photo-1560493676-04071c5f467b?w=800",
             'note': 'Stopping irrigation allows the grain to harden and mature properly.', 
             'yield_per_acre': 20}
        ]
    }
}


# ============================
# ULTRASONIC TANK GEOMETRY
# ============================
# Bottle: 13 cm height, 9 cm diameter
CONTAINER_HEIGHT_CM = 13.0
CONTAINER_RADIUS_CM = 4.5  # 9 cm diameter / 2

# Compute tank capacity (in liters) from geometry
TANK_CAPACITY_LITERS = math.pi * (CONTAINER_RADIUS_CM ** 2) * CONTAINER_HEIGHT_CM / 1000.0
water_tank_level_liters = TANK_CAPACITY_LITERS  # start as "full" by default


def compute_tank_from_ultrasonic():
    d = latest_water_status.get("distance_cm")
    if d is None:
        return None

    H = CONTAINER_HEIGHT_CM
    h = max(0.0, min(H, H - d))

    area_cm2 = math.pi * (CONTAINER_RADIUS_CM ** 2)
    volume_liters = area_cm2 * h / 1000.0
    capacity_liters = area_cm2 * H / 1000.0

    return volume_liters, capacity_liters



# ============================
# DATA SIMULATION
# ============================
sensor_history_data = []
irrigation_history_data = []


def generate_mock_data():
    """Generates mock historical data for sensors and irrigation."""
    global sensor_history_data, irrigation_history_data
    now = datetime.now()

    if not sensor_history_data:
        for i in range(100):
            timestamp = now - timedelta(hours=i)
            sensor_history_data.append({
                "timestamp": timestamp.isoformat(),
                "temp": round(28 + random.uniform(-2, 2), 1),
                "humidity": round(85 + random.uniform(-5, 5), 1),
                "ph": round(6.2 + random.uniform(-0.3, 0.3), 2),
                "n": random.randint(70, 100),
                "p": random.randint(35, 50),
                "k": random.randint(35, 50)
            })

    if not irrigation_history_data:
        for i in range(10):
            start_time = now - timedelta(days=i * 3, hours=random.randint(2, 6))
            duration_mins = random.uniform(15, 45)
            end_time = start_time + timedelta(minutes=duration_mins)
            volume = round(duration_mins * 30, 2)
            irrigation_history_data.append({
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": round(duration_mins, 2),
                "total_volume": volume
            })


# ============================
# SERIAL PARSING & THREADS
# ============================
# def parse_npk_line(line: str):
#     # Expect: NPK,temp,moisture,ph,N,P,K
#     try:
#         parts = line.strip().split(',')
#         if len(parts) != 7 or parts[0] != "NPK":
#             return
#         _, temp, moist, ph, N, P, K = parts
#         latest_npk_reading["timestamp"] = datetime.now().isoformat()
#         latest_npk_reading["temp"] = float(temp)
#         latest_npk_reading["humidity"] = float(moist)
#         latest_npk_reading["ph"] = float(ph)
#         latest_npk_reading["n"] = float(N)
#         latest_npk_reading["p"] = float(P)
#         latest_npk_reading["k"] = float(K)
#     except:
#         pass

def npk_reader_loop():
    global npk_ser
    while True:
        try:
            if npk_ser is None:
                time.sleep(1)
                continue
            line = npk_ser.readline().decode(errors="ignore").strip()
            if line:
                print("[NPK]", line)   # DEBUG: watch in terminal
                parse_npk_line(line)
        except Exception as e:
            print("[NPK ERR]", e)
            time.sleep(1)




def start_auto_irrigation():
    """
    Runs the motor for 3 seconds in a background thread if not already active.
    Uses the same history logging as manual STOP.
    """
    global auto_irrigation_active, current_pump_status, pump_session_start
    global session_total_volume, last_auto_irrigation_time

    if auto_irrigation_active:
        # Already running an auto-cycle
        return

    auto_irrigation_active = True

    def worker():
        global auto_irrigation_active, current_pump_status, pump_session_start
        global session_total_volume, last_auto_irrigation_time

        print("[AUTO] Starting 3-second irrigation due to dry soil")

        # Start motor
        current_pump_status = "ON"
        pump_session_start = datetime.now()
        session_total_volume = 0.0  # reset for this short cycle

        # TODO: if you have real hardware, send PUMP,ON here
        # send_pump_command(True)

        time.sleep(3.0)  # run for 3 seconds

        # Stop motor and log irrigation
        current_pump_status = "OFF"
        # TODO: for real hardware: send PUMP,OFF
        # send_pump_command(False)

        if pump_session_start:
            end_time = datetime.now()
            duration_mins = (end_time - pump_session_start).total_seconds() / 60.0
            irrigation_history_data.insert(0, {
                "start_time": pump_session_start.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": round(duration_mins, 4),
                "total_volume": round(session_total_volume, 4)
            })
            pump_session_start = None

        last_auto_irrigation_time = datetime.now()
        auto_irrigation_active = False
        print("[AUTO] 3-second irrigation complete")

    threading.Thread(target=worker, daemon=True).start()

@app.route('/api/auto_mode', methods=['GET', 'POST'])
def auto_mode():
    """
    GET  -> returns {"auto_mode": true/false}
    POST -> body: {"enabled": true/false} to toggle auto irrigation mode
    """
    global auto_mode_enabled
    if request.method == 'POST':
        data = request.get_json() or {}
        enabled = data.get("enabled")
        if isinstance(enabled, bool):
            auto_mode_enabled = enabled
            print(f"[AUTO] Auto mode set to: {auto_mode_enabled}")
        else:
            return jsonify({"error": "enabled must be boolean"}), 400

    return jsonify({"auto_mode": auto_mode_enabled})


def parse_water_line(line: str):
    # Expect: WATER,distance_cm,pumpState
    try:
        parts = line.strip().split(',')
        if len(parts) != 3 or parts[0] != "WATER":
            return
        _, dist, pump = parts
        latest_water_status["timestamp"] = datetime.now().isoformat()
        latest_water_status["distance_cm"] = float(dist)
        latest_water_status["pump_on"] = (pump.strip() == "1")
    except Exception:
        pass



def water_reader_loop():
    global water_ser, latest_water_status
    while True:
        try:
            if water_ser is None:
                time.sleep(1)
                continue

            # Read one line from the water Arduino
            line = water_ser.readline().decode(errors="ignore").strip()
            if not line:
                continue  # nothing received, loop again

            # Expect: WATER,distance_cm,pumpState
            parts = line.split(',')
            if len(parts) == 3 and parts[0] == "WATER":
                try:
                    dist = float(parts[1])
                    pump_state = bool(int(parts[2]))
                    latest_water_status["timestamp"] = datetime.now().isoformat()
                    latest_water_status["distance_cm"] = dist
                    latest_water_status["pump_on"] = pump_state
                    print("[WATER]", latest_water_status)
                except ValueError:
                    # Bad number format, ignore this line
                    pass

        except Exception as e:
            print("[WATER ERR]", e)
            time.sleep(1)





water_ser = None  # global serial for water Arduino

water_ser = None  # make sure this is global if not already

def init_serial_and_threads():
    global npk_ser, water_ser

    # --- NPK ---
    try:
        npk_ser = serial.Serial(NPK_PORT, BAUD_RATE, timeout=1)
        print(f"[SERIAL] Connected to NPK Arduino on {NPK_PORT}")
    except Exception as e:
        print(f"[SERIAL] Failed to connect to NPK Arduino on {NPK_PORT}: {e}")
        npk_ser = None

    # --- WATER / MOTOR ---
    try:
        water_ser = serial.Serial(WATER_PORT, BAUD_RATE, timeout=1)
        print(f"[SERIAL] Connected to Water Arduino on {WATER_PORT}")
    except Exception as e:
        print(f"[SERIAL] Failed to connect to Water Arduino on {WATER_PORT}: {e}")
        water_ser = None




def detect_arduinos():
    """
    Detects which serial ports belong to NPK Arduino and Water Arduino automatically.
    Returns (npk_port, water_port)
    """
    npk_port = None
    water_port = None

    print("[AUTO] Scanning for Arduinos...")

    ports = list_ports.comports()

    for p in ports:
        try:
            print(f"[AUTO] Checking port: {p.device}")
            s = serial.Serial(p.device, BAUD_RATE, timeout=1)
            time.sleep(2)

            for _ in range(5):
                line = s.readline().decode(errors="ignore").strip()
                if not line:
                    continue

                print(f"[AUTO] Read: {line}")

                if "NPK" in line.upper():
                    npk_port = p.device
                elif "WATER" in line.upper():
                    water_port = p.device

            s.close()
        except Exception as e:
            print(f"[AUTO] Error reading {p.device}: {e}")

    print(f"[AUTO] NPK Arduino found at: {npk_port}")
    print(f"[AUTO] Water Arduino found at: {water_port}")

    return npk_port, water_port


def init_serial_and_threads():
    global npk_ser, water_ser

    # --- NPK ---
    try:
        npk_ser = serial.Serial(NPK_PORT, BAUD_RATE, timeout=1)
        print(f"[SERIAL] Connected to NPK Arduino on {NPK_PORT}")
    except Exception as e:
        print(f"[SERIAL] Failed to connect to NPK Arduino on {NPK_PORT}: {e}")
        npk_ser = None

    # --- WATER / MOTOR ---
    try:
        water_ser = serial.Serial(WATER_PORT, BAUD_RATE, timeout=1)
        print(f"[SERIAL] Connected to Water Arduino on {WATER_PORT}")
    except Exception as e:
        print(f"[SERIAL] Failed to connect to Water Arduino on {WATER_PORT}: {e}")
        water_ser = None






# line format:
# NPK,temp,moisture,ph,N,P,K

def parse_npk_line(line: str):
    """
    Expected format from Arduino:
    NPK,<temp>,<moisture>,<ph>,<N>,<P>,<K>
    e.g. NPK,26.50,0.00,9.00,0,0,0
    """
    global latest_npk_reading

    parts = line.strip().split(",")
    if len(parts) != 7 or parts[0].strip() != "NPK":
        return  # ignore anything else

    _, temp, moist, ph, N, P, K = parts

    try:
        latest_npk_reading["timestamp"] = datetime.now().isoformat()
        latest_npk_reading["temp"] = float(temp)
        latest_npk_reading["humidity"] = float(moist)  # JS uses 'humidity'
        latest_npk_reading["ph"] = float(ph)
        latest_npk_reading["n"] = float(N)
        latest_npk_reading["p"] = float(P)
        latest_npk_reading["k"] = float(K)
    except ValueError:
        # If something is malformed, just skip that line
        print("[NPK] Parse error for line:", line)





@app.route('/api/motor_status')
def motor_status():
    global current_flow_rate, session_total_volume, water_tank_level_liters
    global auto_mode_enabled, auto_irrigation_active, last_auto_irrigation_time
    print("[API] /api/motor_status called")
    if current_pump_status == "ON":
        current_flow_rate = random.uniform(28.0, 32.0)
        volume_delta = current_flow_rate / 60.0
        session_total_volume += volume_delta
        water_tank_level_liters = max(0, water_tank_level_liters - volume_delta)
    else:
        current_flow_rate = 0.0

    return jsonify({
        "motor_on": current_pump_status == "ON",
        "flow_rate": current_flow_rate,
        "total_volume": session_total_volume,
        "distance_cm": latest_water_status["distance_cm"],
        "pump_on_hw": latest_water_status["pump_on"],
        "auto_mode": auto_mode_enabled,
        "auto_irrigation_active": auto_irrigation_active
    })





# ============================
# MOTOR & FLOW SENSOR ENDPOINTS
# ============================
@app.route('/api/motor', methods=['POST'])
def motor_control():
    global current_pump_status, pump_session_start, session_total_volume
    data = request.get_json()
    print("[API] /api/motor called with:", data)
    command = data.get("command")

    if command == "START":
        current_pump_status = "ON"
        pump_session_start = datetime.now()
        session_total_volume = 0.0
        send_pump_command(True)
    elif command == "STOP":
        current_pump_status = "OFF"
        send_pump_command(False)
        if pump_session_start:
            end_time = datetime.now()
            duration_mins = (end_time - pump_session_start).total_seconds() / 60
            irrigation_history_data.insert(0, {
                "start_time": pump_session_start.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": round(duration_mins, 2),
                "total_volume": round(session_total_volume, 2)
            })
            pump_session_start = None
    else:
        return jsonify({"error": "Invalid command"}), 400

    return jsonify({
        "motor_on": current_pump_status == "ON",
        "flow_rate": current_flow_rate,
        "total_volume": session_total_volume
    })




# ============================
# DATA & HISTORY ENDPOINTS
# ============================
@app.route('/')
def index():
    return render_template('base.html')


@app.route('/api/latest_reading')
def latest_reading():
    print("[API] /api/latest_reading called")
    # Prefer real NPK reading
    if latest_npk_reading["timestamp"] is not None:
        return jsonify(latest_npk_reading)

    # Fallback to mock
    if not sensor_history_data:
        generate_mock_data()
    return jsonify(sensor_history_data[0])



@app.route('/api/sensor_history')
def get_sensor_history():
    return jsonify(sensor_history_data)


@app.route('/api/water_history')
def get_water_history():
    return jsonify(irrigation_history_data)


@app.route('/api/dashboard_summary')
def dashboard_summary():
    crop = request.args.get('crop', 'paddy')
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "Planting date is required."}), 400

    try:
        planting_date = datetime.strptime(date_str, '%Y-%m-%d')
        age = (datetime.now() - planting_date).days

        crop_info_db = CROP_DATA.get(crop)
        if not crop_info_db:
            return jsonify({"error": "Crop not found"}), 404

        # ---------------------------
        # CURRENT CROP STAGE
        # ---------------------------
        current_stage = next(
            (s for s in crop_info_db["stages"]
             if s["startDay"] <= age <= s["endDay"]),
            None
        )

        if not current_stage:
            last_stage = crop_info_db["stages"][-1]
            current_stage = last_stage.copy()
            if age > last_stage['endDay']:
                current_stage['name'] = 'Harvested'

        # ---------------------------
        # LATEST SENSOR READING
        # ---------------------------
        if latest_npk_reading["timestamp"] is not None:
            latest = latest_npk_reading
        else:
            if not sensor_history_data:
                generate_mock_data()
            latest = sensor_history_data[0]

        # ---------------------------
        # ALERTS & STATUS
        # ---------------------------
        alerts, status = [], {}

        if not (18 < latest.get('temp', 0) < 35):
            alerts.append(f"Temperature is {latest.get('temp')}°C, outside optimal range.")
            status['temp'] = 'warn'
        else:
            status['temp'] = 'good'

        if latest.get('humidity', 0) < 60:
            alerts.append("Low humidity / soil moisture detected.")
            status['humidity'] = 'warn'
        else:
            status['humidity'] = 'good'

        if not (5.5 < latest.get('ph', 0) < 7.5):
            alerts.append("Soil pH is outside the optimal range.")
            status['ph'] = 'warn'
        else:
            status['ph'] = 'good'

        status.update({'n': 'good', 'p': 'good', 'k': 'good'})

        # ---------------------------
        # TANK WATER LEVEL FROM ULTRASONIC
        # ---------------------------
        tank_current = water_tank_level_liters
        tank_capacity = TANK_CAPACITY_LITERS

        ultrasonic_result = compute_tank_from_ultrasonic()
        if ultrasonic_result is not None:
            tank_current, tank_capacity = ultrasonic_result



        # ---------------------------
        # FINAL RESPONSE
        # ---------------------------
        return jsonify({
            "latest_reading": latest,
            "crop_info": {
                "name": crop_info_db["name"],
                "age": age,
                "stage": current_stage
            },
            "alerts": alerts if alerts else ["All systems normal."],
            "status": status,
            "water_tank": {
                "current": tank_current,
                "capacity": tank_capacity
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/crop_recommend', methods=['POST'])
def crop_recommend():
    data = request.get_json()
    print("[API] Crop Recommendation Request:", data)

    try:
        N = float(data["N"])
        P = float(data["P"])
        K = float(data["K"])
        temp = float(data["temperature"])
        humidity = float(data["humidity"])
        ph = float(data["ph"])
        rainfall = float(data["rainfall"])
    except:
        return jsonify({"error": "Invalid or missing input values"}), 400

    # >>> your ML model / logic here
    # return dummy recommendation for now:
    return jsonify({
        "top_crops": [
            {"crop": "Paddy", "score": 92},
            {"crop": "Maize", "score": 85},
            {"crop": "Cotton", "score": 70},
            {"crop": "Wheat", "score": 65}
        ]
    })


# ============================
# RECOMMENDATION & STATUS ENDPOINTS
# ============================
@app.route('/api/recommend_crop', methods=['POST'])
def recommend_crop():
    data = request.get_json()
    scores = {
        'paddy': 1.2 if float(data['rainfall']) > 150 and float(data['N']) > 70 else 0.5,
        'maize': 1.1 if 20 < float(data['temperature']) < 32 and float(data['humidity']) > 60 else 0.4,
        'cotton': 1.3 if float(data['temperature']) > 25 and float(data['rainfall']) < 100 else 0.3,
        'wheat': 1.0 if 15 < float(data['temperature']) < 25 and float(data['rainfall']) < 80 else 0.6,
        'groundnut': 0.9 if 25 < float(data['temperature']) < 35 else 0.5,
        'pulses': 0.8 if float(data['rainfall']) < 70 else 0.4
    }
    for crop in scores:
        scores[crop] += random.uniform(-0.2, 0.2)

    total_score = sum(scores.values())
    recommendations = []
    for crop, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
        market_info = CROP_MARKET_INFO.get(crop, {})
        recommendations.append({
            "crop": crop.title(),
            "probability": (score / total_score),
            "market_price": market_info.get("price", 0),
            "demand": market_info.get("demand", "N/A")
        })
    return jsonify({"recommendations": recommendations[:4]})


@app.route('/api/recommend_fertilizer', methods=['POST'])
def recommend_fertilizer():
    data = request.get_json()
    N = float(data.get('Nitrogen', 0))
    P = float(data.get('Phosphorus', 0))
    K = float(data.get('Potassium', 0))
    crop = data.get('Crop', 'Unknown')

    if N < 40:
        rec, reason = "Urea", f"Nitrogen level is very low ({N} ppm), critical for {crop} growth."
    elif P < 20:
        rec, reason = "DAP", f"Phosphorus level is very low ({P} ppm), essential for root development."
    elif K < 20:
        rec, reason = "MOP", f"Potassium level is very low ({K} ppm), crucial for flowering."
    elif N < 60 and P < 30 and K < 30:
        rec, reason = "10-26-26", "All nutrients moderately low. Balanced NPK fertilizer recommended."
    else:
        rec, reason = "19-19-19", "Nutrient levels adequate. Use a balanced fertilizer for maintenance."

    return jsonify({
        "recommendation": rec,
        "reasoning": reason,
        "application_method": FERTILIZER_INFO.get(rec, "Follow standard guidelines.")
    })


@app.route('/api/crop_status')
def get_crop_status():
    crop_name = request.args.get('crop')
    date_str = request.args.get('date')
    acres = request.args.get('acres', type=float)

    if not all([crop_name, date_str, acres]):
        return jsonify({"error": "Missing required parameters."}), 400

    try:
        planting_date = datetime.strptime(date_str, '%Y-%m-%d')
        if planting_date > datetime.now():
            return jsonify({"error": "Planting date cannot be in the future."}), 400

        age_in_days = (datetime.now() - planting_date).days
        crop_info = CROP_DATA.get(crop_name)
        if not crop_info:
            return jsonify({"error": f"Crop data not found for '{crop_name}'."}), 404

        current_stage = next((s for s in crop_info["stages"]
                              if s["startDay"] <= age_in_days <= s["endDay"]), None)
        
        if not current_stage:
            final_stage = crop_info["stages"][-1]
            if age_in_days > final_stage['endDay']:
                current_stage = final_stage.copy()
                current_stage['name'] = 'Harvested - Beyond Lifecycle'
            else:
                return jsonify({"error": f"Age ({age_in_days} days) is before crop lifecycle starts."}), 400

        final_stage = crop_info["stages"][-1]
        harvest_date = planting_date + timedelta(days=final_stage['endDay'])
        
        total_yield = final_stage.get('yield_per_acre', 0) * acres

        return jsonify({
            "name": crop_info["name"],
            "image_url": current_stage.get('image', crop_info.get('main_image')),
            "age": age_in_days,
            "current_stage": current_stage,
            "harvest_date": harvest_date.strftime('%B %d, %Y'),
            "estimated_yield_per_acre": final_stage.get('yield_per_acre', 0),
            "total_estimated_yield": round(total_yield, 2),
            "acres": acres,
            "weather_advisory": "Weather seems stable. Maintain regular irrigation schedule.",
            "farmer_note": current_stage.get('note', 'No special notes for this stage.')
        })
    except ValueError as ve:
        return jsonify({"error": f"Invalid date format: {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# ============================
# MAIN
# ============================
if __name__ == '__main__':
    generate_mock_data()
    init_serial_and_threads()
    app.run(debug=True)

