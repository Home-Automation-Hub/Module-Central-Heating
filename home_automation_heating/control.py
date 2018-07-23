from home_automation_hub import mqtt
import time
from . import storage, websockets as ws
import statistics
import threading
import datetime
import dateutil.parser

def heating_on():
    mqtt.publish("flat/heating/hallway/chState", "on")
    storage.set("ch_running", True)

    ws.push_state()


def heating_off():
    mqtt.publish("flat/heating/hallway/chState", "off")
    storage.set("ch_running", False)

    ws.push_state()

def heating_set_on():
    mqtt.publish("flat/heating/hallway/sensorLed", "on")
    storage.set("ch_set_on", True)

    ws.push_state()

def heating_set_off():
    mqtt.publish("flat/heating/hallway/sensorLed", "off")
    storage.set("ch_set_on", False)

    heating_off() # This will also call ws.push_state()

def handle_temperature(topic, message):
    reading = float(message)
    storage.store_temperature_reading(reading)
    temperature = statistics.mean(storage.get_temperature_readings())
    temperature = round(temperature, 2)
    storage.set("temperature", temperature)

    ch_set_on = storage.get("ch_set_on")
    
    if ch_set_on:
        # Thermostat logic
        delta_above = storage.get("thermostat_delta_above")
        delta_below = storage.get("thermostat_delta_below")
        set_temp = storage.get("thermostat_temperature")
        
        if temperature < (set_temp - delta_below):
            heating_on()
        
        if temperature > (set_temp + delta_above):
            heating_off()

        ch_running = storage.get("ch_running")
        if ch_running:
            # This will send the MQTT "on" signal which must be sent
            # regularly to prevent the heating turning off due to lack
            # of communication.
            heating_on()

    ws.get_instance().publish("temperature", {
        "latest_reading": temperature
    })

def update_manual_control_message():
    state, message = generate_manual_state_message()
    ws.get_instance().publish("index_manual_message", {
        "state": state,
        "message": message
    })

def process_timer_management():
    while True:
        now = datetime.datetime.now()
        control_mode = storage.get("control_mode")
        
        if control_mode == "manual":
            timing = storage.get("manual_control_timing")
            state = storage.get("manual_control_state")

            # If set to start at a specified time and currently waiting
            # until told to start 
            if state == "pending" and timing.get("start") != "immediate":
                start_timestamp = dateutil.parser.parse(timing.get("start"))
                if now > start_timestamp:
                    heating_set_on()
                    storage.set("manual_control_state", "running")
                    update_manual_control_message()

            if state == "running" and timing.get("end") != "indefinite":
                end_timestamp = dateutil.parser.parse(timing.get("end"))
                if now > end_timestamp:
                    heating_set_off()
                    storage.set("manual_control_state", "complete")
                    update_manual_control_message()    
        elif control_mode == "timer":
            current_day = now.weekday()
            yesterday = (current_day - 1) % 7

            timers = storage.get("timers")
            valid_timer_found = False
            for timer in timers:
                start_time, end_time, started_yesterday =\
                        start_end_time_to_dates(timer["startTime"],
                                timer["endTime"], now)

                if timer["days"][str(current_day)] or \
                        (timer["days"][str(yesterday)] and started_yesterday):
                    # Timer is valid for the current day, now check if
                    # we are to turn the heating on or off
                    if start_time < now < end_time:
                        if not storage.get("ch_set_on"):
                            heating_set_on()

                            storage.set("thermostat_temperature",
                                    timer["temperature"])
                            ws.get_instance().publish("thermostat_updated", {
                                "value": timer["temperature"]
                            })

                        valid_timer_found = True

            if not valid_timer_found:
                set_thermostat_to_manual_temp()
                heating_set_off()

        time.sleep(1)

def start_end_time_to_dates(start_time, end_time, now=None):
    """
        Converts start and end times into dates based on the current
        date
        :param start_time: Time at which the timer is set to start
        :param end_time: Time at which the timer is set to end
        :param now: Datetime representing the current time, will default
                to output of datetime.datetime.now() if not supplied
        :return: Tuple of:
                start_time - Datetime representing the start time
                end_time - Datetime representing the end time
                started_yesterday - Boolean, true if timer would have
                        started during the previous day
    """
    # Get start and end time for each timer and convert to
    # also contain current date. If end_time comes before
    # start_time assume that we are straddling midnight and
    # therefore add a day onto end_date so that it occurs
    # the following day
    if not now:
        now = datetime.datetime.now()
    midnight_today = now.replace(hour=0, minute=0, second=0)

    start_time = datetime.datetime.strptime(start_time,
            "%H:%M")
    start_time = start_time.replace(day=now.day,
            month=now.month, year=now.year)

    end_time = datetime.datetime.strptime(end_time,
            "%H:%M")
    end_time = end_time.replace(day=now.day,
            month=now.month, year=now.year)

    started_yesterday = False
    if end_time < start_time:
        if midnight_today < now < end_time:
            start_time = start_time - datetime.timedelta(days=1)
            started_yesterday = True
        else:
            end_time = end_time + datetime.timedelta(days=1)

    return start_time, end_time, started_yesterday


def set_thermostat_to_manual_temp():
    new_temp = storage.get("manual_thermostat_temperature")
    storage.set("thermostat_temperature", new_temp)
    ws.get_instance().publish("thermostat_updated", {
        "value": new_temp
    })

def generate_manual_state_message():
    manual_control_state=storage.get("manual_control_state")
    manual_control_timing=storage.get("manual_control_timing") or {}

    if not (manual_control_state or manual_control_timing):
        return None, None

    try:
        timestamp = dateutil.parser.parse(manual_control_timing.get("start"))

        date_format = "%H:%M"
        if timestamp.date() != datetime.datetime.now().date():
            date_format += " (on %Y-%m-%d)"
        manual_control_timing["start"] = timestamp.strftime(date_format)
    except ValueError:
        pass # This will occur if the field is set to "immediate"

    try:
        timestamp = dateutil.parser.parse(manual_control_timing.get("end"))

        date_format = "%H:%M"
        if timestamp.date() != datetime.datetime.now().date():
            date_format += " (on %Y-%m-%d)"
        manual_control_timing["end"] = timestamp.strftime(date_format)
    except ValueError:
        pass # This will occur if the field is set to "indefinite"

    message = "Heating is off"
    if manual_control_state in ["running", "pending"]:
        if manual_control_state == "running":
            message = "Heating is currently running until "
        else:
            message = "Heating will turn on at " \
                    + manual_control_timing.get("start") \
                    + " and will run until "
            
        if manual_control_timing.get("end") == "indefinite":
            message += "it is switched off manually"
        else:
            message += manual_control_timing.get("end")
        
    
    return manual_control_state, message

def initialise(module_id):
    heating_set_off()
    mqtt.subscribe("flat/heating/hallway/temperature", handle_temperature)
    threading.Thread(target=process_timer_management).start()
