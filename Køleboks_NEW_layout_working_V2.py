import _thread
from machine import Pin, PWM, I2C, ADC
from time import sleep
from ssd1306 import SSD1306_I2C
import machine
import network
import socket
import time

status = "ON"
cooling_enabled_global = True 
battery_control_enabled = True  # Initialize battery control status

# Assuming your OLED is connected to I2C pins (SDA+GP7, SCL+GP6)
i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9), freq=400000)
oled = SSD1306_I2C(128, 32, i2c)

# Analog input pin for the NTC sensor
ntc_pin = machine.ADC(27)

# Analog input pin for the second NTC sensor on GP28
ntc_pin2 = machine.ADC(28)

# Analog input pin for battery voltage measurement
# Example pin, replace with the correct pin
battery_pin = machine.ADC(26) 

# Relay control pin
relay_pin = machine.Pin(18, machine.Pin.OUT)

# Access Point (AP) settings
ssid_ap = 'PicoSuperBox'
password_ap = 'KoleboksV2'

# Set up PWM Pins for fan control
fan1_pin = Pin(21)
fan2_pin = Pin(20)  # Anvend den relevante pin for din anden blæser
fan1_pwm = PWM(fan1_pin)
fan2_pwm = PWM(fan2_pin)
duty_step = 10  # Just an example, adjust as needed

# Set PWM frequency
frequency = 1000
fan1_pwm.freq(frequency)
fan2_pwm.freq(frequency)

# Set initial fan speeds (percentage)
fan1_speed_percentage = 10
fan2_speed_percentage = 10

# Variables to store temperatures
temperature = 0
temperature2 = 0

target_temperature = 7

# Flag to control the thread
running = True

# Lock for state and OLED operations
lock = _thread.allocate_lock()

def connect_ap():
    # Connect to WLAN as Access Point (AP)
    wlan_ap = network.WLAN(network.AP_IF)
    wlan_ap.config(essid=ssid_ap, password=password_ap)
    wlan_ap.active(True)
    while not wlan_ap.active():
        print('Waiting for AP connection...')
        sleep(1)
    ip_ap = wlan_ap.ifconfig()[0]
    print(f'Access Point (AP) created. IP: {ip_ap}')
    return ip_ap

def open_socket(ip):
    address = (ip, 80)
    connection = socket.socket()
    connection.settimeout(10)  # Set a timeout of 10 seconds for the socket
    connection.bind(address)
    connection.listen(1)
    return connection


def webpage(state, cooling_enabled, reset_url, battery_voltage):
    # Format battery voltage as a string with one decimal
    battery_voltage_str = "{:.1f}".format(battery_voltage)

    # Tilføj et trekant-ikon, hvis batterispændingen er lav
    triangle_icon = "&#x26A0;" if battery_voltage < 11 else ""  # Unicode for trekant-ikonet

    # Template HTML with CSS
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style"/>
    <title>Pico Køleboks V2</title>
    <meta http-equiv="refresh" content="5"> <!-- Refresh every 5 seconds -->
    <style>
        html, body {{
            height: 100%;
            margin: 0;
            padding: 0;
            background: #223;
            font-family: Arial, sans-serif; /* Set font family */
            overflow: hidden; /* Forhindrer rullehandling */
        }}

        .box {{
            min-width: 300px; /* Set minimum width */
            min-height: 250px; /* Set minimum height */
            width: auto; /* Let the width adjust dynamically */
            height: auto; /* Let the height adjust dynamically */
            padding: 20px; /* Add padding to create space around the text */
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            display: grid;
            place-content: center;
            color: white;
            text-shadow: 0 1px 0 #000;

            --border-angle: 0turn; /* For animation. */
            --main-bg: conic-gradient(
                from var(--border-angle),
                #213,
                #112 5%,
                #112 60%,
                #213 95%
            );

            border: solid 5px transparent;
            border-radius: 2em;
            --gradient-border: conic-gradient(from var(--border-angle), transparent 25%, #08f, #f03 99%, transparent);

            background: 
                /* padding-box clip this background in to the overall element except the border. */
                var(--main-bg) padding-box,
                /* border-box extends this background to the border space */
                var(--gradient-border) border-box, 
                /* Duplicate main background to fill in behind the gradient border. You can remove this if you want the border to extend "outside" the box background. */
                var(--main-bg) border-box;

            background-position: center center;
        }}

        h1, p, form, a {{
            margin: 10px; /* Added margin to create space between elements */
            text-align: center; /* Center align text */
        }}

        h1 {{
            font-size: 36px; /* Increased font size for heading */
            color: #f5e542; /* Set text color for heading */
            text-transform: uppercase; /* Convert text to uppercase */
            letter-spacing: 2px; /* Add letter spacing */
        }}

        .button-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 24px; /* Ændr denne værdi for mere mellemrum */
        }}

        .button-container form:first-child {{
            margin-right: 10px; /* Tilføj en margen til højre på den første knap */
        }}

        .button-container form:last-child {{
            margin-left: 10px; /* Tilføj en margen til venstre på den anden knap */
        }}

        .button-container input[type="submit"], button {{
            padding: 10px 30px;
            font-size: 16px;
            cursor: pointer;
            border: none;
            background-color: #28a745;
            color: white;
            border-radius: 20px;
        }}

        .button-container input[type="submit"]:hover, button:hover {{
            background-color: #218838;
        }}

        .temperature-controls {{
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 10px;
        }}

        .temperature-controls form input[type="submit"] {{
            padding: 10px 30px;
            font-size: 16px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 30px;
        }}

        .temperature-controls form:first-child input[type="submit"] {{
            margin-right:-7px;
        }}

        .temperature-controls form:last-child input[type="submit"] {{
            margin-left: -7px;
        }}

        a button[type="button"] {{
            padding: 10px 30px;
            margin-top: 10px;
        }}

        p {{
            font-size: 24px;
            color: #17a2b8;
        }}

        #status-line {{
            font-size: 18px;
            margin-top: 10px;
            text-align: center; /* Center align status line */
        }}

        .temperature-icon {{
            font-size: 80px;
            margin-right: 0px;
        }}

        .temperature-p {{
            margin-bottom: -5px;
            margin-top: -20px;
        }}

        .battery-icon {{
            font-size: 48px;
            color: #f5e542;
            margin-right: 5px;
        }}

        .triangle-icon {{
            font-size: 48px;
            color: #f00;
        }}
    </style>
</head>
<body>
    <div class="box">
        <h1>Køleboks</h1>
        <p><span class="triangle-icon">{triangle_icon}</span><span class="battery-icon">🔋</span>{battery_voltage_str} V<span class="triangle-icon">{triangle_icon}</span></p>
        <div class="button-container">
            <form action="./turn_on">
                <input type="submit" value="Turn On">
            </form>
            <form action="./turn_off">
                <input type="submit" value="Turn Off">
            </form>
        </div>
        <div class="temperature-controls">
            <form action="./decrease_target_temperature">
                <input type="submit" value="-">
            </form>
            <span style="color: #17a2b8; font-size: 24px;">
                Target: {target_temperature}°C
            </span>
            <form action="./increase_target_temperature">
                <input type="submit" value="+">
            </form>
        </div>
        <p class="temperature-p"><span class="temperature-icon">&#x1F9CA;</span> {temperature:.1f}°C</p>
        <p class="temperature-p"><span class="temperature-icon">&#x1F321;</span> {temperature2:.1f}°C</p>
        <div class="button-container">
            </a>
            <a href="./toggle_battery_control" style="text-align: center; display: inline-block;">
                <button type="button" style="background-color: {'#28a745' if battery_control_enabled else '#f03'}; color: white;">{'Battery' if battery_control_enabled else 'AC Mode'}</button>
            </a>
        </div>
        <div id="status-line" style="margin-top: -20px;">{'&#x2705;' if cooling_enabled else '&#x274C;'} Status: {'ON' if cooling_enabled else 'OFF'} {'&#x2705;' if cooling_enabled else '&#x274C;'}</div>
    </div>
</body>
</html>
"""
    return str(html)


def measure_battery_voltage():
    # Example function to measure battery voltage
    # You need to replace this with your actual battery voltage measurement code
    battery_value = battery_pin.read_u16()
    battery_voltage = battery_value * 3.3 / 65535 * 11.3  # Assuming VCC is 3.3V

    # Turn off the relay if battery voltage falls below 11V and battery control is enabled
    if battery_voltage < 11 and battery_control_enabled:
        turn_relay_off()
        global cooling_enabled_global
        cooling_enabled_global = False

    return battery_voltage


def turn_relay_on():
    global status
    if status != "ON":
        relay_pin.value(1)  # Turn on the relay
        status = "ON"


def turn_relay_off():
    global status
    if status != "OFF":
        relay_pin.value(0)  # Turn off the relay
        status = "OFF"


def display_temperature(temperature1, temperature2):
    with lock:
        # Comment out or remove the following line to keep the previous content on the OLED
        oled.fill(0)

        # Display the first temperature on the OLED display with one decimal place
        temperature_str1 = "{:.1f}".format(temperature1)
        oled.text("Inde: " + temperature_str1 + "^C", 0, 0, 1)

        # Display the second temperature on the OLED display with one decimal place
        temperature_str2 = "{:.1f}".format(temperature2)
        oled.text("Ude: " + temperature_str2 + "^C", 0, 12, 1)

        # Show the OLED content
        oled.show()


def control_fans_and_display():
    global fan1_pwm, fan2_pwm, fan1_speed_percentage, fan2_speed_percentage, temperature, temperature2

    try:
        while True:
            battery_voltage = measure_battery_voltage()
            # Read NTC sensor data from the first sensor and convert it to temperature
            ntc_value = ntc_pin.read_u16()
            temperature = convert_ntc_to_temperature(ntc_value, sensor_number=1)

            # Read NTC sensor data from the second sensor and convert it to temperature
            ntc_value2 = ntc_pin2.read_u16()
            temperature2 = convert_ntc_to_temperature(ntc_value2, sensor_number=2)

            # Control fan speed for fan 1 based on temperature from sensor 2
            if temperature2 <= 25:
                fan2_speed_percentage = 0
            elif temperature2 >= 30:
                fan2_speed_percentage = 100
            else:
                # Linear interpolation between 0% and 100% based on temperature
                fan2_speed_percentage = int(100 * (temperature2 - 25) / (30 - 25))

            # Control fan speed for fan 1
            if fan2_speed_percentage <= 100:
                # Follow fan 2 up to 50%
                fan1_speed_percentage = fan2_speed_percentage
            else:
                # Fan 1 stays at 50% if fan 2 is above 50%
                fan1_speed_percentage = 100

            # Calculate duty cycle based on fan speeds percentage
            duty_cycle1 = int(((100 - fan1_speed_percentage) / 100) * 65535)
            duty_cycle2 = int(((100 - fan2_speed_percentage) / 100) * 65535)

            # Set the duty cycles
            fan1_pwm.duty_u16(duty_cycle1)
            fan2_pwm.duty_u16(duty_cycle2)

            # Display temperatures
            display_temperature(temperature, temperature2)

            # Turn on/off the relay based on temperature from sensor 1
            if cooling_enabled_global:
                if temperature > target_temperature:
                    turn_relay_on()
                else:
                    turn_relay_off()

            sleep(1)  # Adjust sleep time as needed

    except Exception as e:
        print("Error:", e)
        fan1_pwm.duty_u16(0)  # Turn off the fans
        fan2_pwm.duty_u16(0)
        fan1_pwm.deinit()
        fan2_pwm.deinit()

def convert_ntc_to_temperature(ntc_value, sensor_number):
    # Implement your NTC to temperature conversion logic here for each sensor
    # This is just a placeholder, replace it with your actual calculation

    # Constants for temperature conversion (replace with actual values)
    if sensor_number == 1:
        temperature_range = (-25, 91)  # Replace with your NTC temperature range for sensor 1
        conversion_coefficient = 1.0   # Replace with your conversion coefficient for sensor 1
    elif sensor_number == 2:
        temperature_range = (-31, 95)  # Replace with your NTC temperature range for sensor 2
        conversion_coefficient = 1.0   # Replace with your conversion coefficient for sensor 2
    else:
        raise ValueError("Invalid sensor_number")

    # Perform the temperature conversion
    temperature = temperature_range[0] + (temperature_range[1] - temperature_range[0]) * (ntc_value / 65535)
    temperature = temperature * conversion_coefficient

    return temperature

def check_and_reconnect_wifi():
    wlan_ap = network.WLAN(network.AP_IF)
    print('Reconnecting to Wi-Fi...')
    wlan_ap.active(False)
    wlan_ap.active(True)
    wlan_ap.config(essid=ssid_ap, password=password_ap)
    while not wlan_ap.active():
        print('Waiting for AP connection...')
        sleep(1)
    print('Reconnected to Wi-Fi.')


def increase_target_temperature():
    global target_temperature
    with lock:
        target_temperature += 1  # Increase the target temperature by 1 degree

def decrease_target_temperature():
    global target_temperature
    with lock:
        target_temperature -= 1  # Decrease the target temperature by 1 degree

def toggle_battery_control():
    global battery_control_enabled
    battery_control_enabled = not battery_control_enabled

def process_request(request, state, cooling_enabled_global, battery_control_enabled):
    global status, target_temperature, temperature, temperature2

    redirect_url = None

    if request == '/turn_on?':
        # Turn on the relay
        turn_relay_on()
        status = 'ON'
        cooling_enabled_global = True
        redirect_url = './'
    elif request == '/turn_off?':
        # Turn off the relay
        turn_relay_off()
        status = 'OFF'
        cooling_enabled_global = False
        redirect_url = './'
    elif request == '/increase_target_temperature?':
        # Increase the target temperature
        increase_target_temperature()
        redirect_url = './'
    elif request == '/decrease_target_temperature?':
        # Decrease the target temperature
        decrease_target_temperature()
        redirect_url = './'
    elif request == '/toggle_battery_control':
        # Toggle battery control
        toggle_battery_control()
        redirect_url = './'
    
    return status, cooling_enabled_global, redirect_url



# Start fan control thread
_thread.start_new_thread(control_fans_and_display, ())

try:
    ip_ap = connect_ap()
    connection = open_socket(ip_ap)

    state = 'OFF'  # Initialize 'state'
    cooling_enabled_global = False  # Initialize cooling status

    last_wifi_check_time = time.time()

    while True:
        current_time = time.time()

        # Check and reconnect Wi-Fi every 5 minutes
        if current_time - last_wifi_check_time > 900:
            print("wifi restart?")
            check_and_reconnect_wifi()
            print("wifi restart OK")
            last_wifi_check_time = current_time
            

        try:
            client, addr = connection.accept()
            client.settimeout(10)  # Set a timeout for the client socket
            request = client.recv(1024)
            request = str(request)
            try:
                request = request.split()[1]
            except IndexError:
                pass
            state, cooling_enabled_global, redirect_url = process_request(request, state, cooling_enabled_global, battery_control_enabled)
            battery_voltage = measure_battery_voltage()

            if redirect_url:
                # Send a redirect response
                client.send("HTTP/1.1 303 See Other\n")
                client.send("Location: {}\n".format(redirect_url))
                client.send("Connection: close\n\n")
            else:
                # Send HTML response to the client
                html = webpage(state, cooling_enabled_global, redirect_url, battery_voltage)
                client.send("HTTP/1.1 200 OK\n")
                client.send("Content-Type: text/html\n")
                client.send("Connection: close\n\n")
                client.sendall(html)
            client.close()
        except OSError as e:
            print("Connection error:", e)
            try:
                client.close()  # Ensure the client socket is closed on error
            except:
                pass
            continue


except KeyboardInterrupt:
    # Stop the combined control thread and reset the Pico on interruption
    fan1_pwm.duty_u16(0)  # Turn off the fans
    fan2_pwm.duty_u16(0)
    fan1_pwm.deinit()
    fan2_pwm.deinit()
    machine.reset()

