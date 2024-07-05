#!/usr/bin/env python3
import paho.mqtt.client as mqtt
from access_ldb import MySQLAccess
from datetime import datetime, timedelta

feedback_receive_timeout = 60
battery_live_monitor_timeout = 180


def publish_message(cart_name, message):
    client = mqtt.Client()
    client.connect("192.168.185.25", 1883, 60)
    client.publish("cart_name", message)
    client.disconnect()


def read_data(table_name, battery_name, column_name):
    sql = MySQLAccess()
    query = f"SELECT {column_name} FROM {table_name} WHERE Battry_ID = %s"
    sql.cursor.execute(query, (battery_name,))
    result = sql.cursor.fetchone()
    result[0]


def check_feedback(cart_name, msg_to_check):
    feedback = False
    time_passed = 0
    feedback_start_time = datetime.now()
    while time_passed < feedback_receive_timeout:
        if msg_to_check == read_data(
            "TX_ChargeOrdersFeedback", cart_name, "Bat_State_actual"
        ):
            feedback = True
            break
        else:
            time_passed = (datetime.now() - feedback_start_time).total_seconds()
    return feedback


def monitor_result(table_name, battery_name, column_name, expected_result):
    result_success = False
    time_passed = 0
    monitor_result_start_time = datetime.now()
    while time_passed < battery_live_monitor_timeout:
        if expected_result == read_data(table_name, battery_name, column_name):
            result_success = True
        else:
            time_passed = (datetime.now() - monitor_result_start_time).total_seconds()

    return result_success


def wakeup(cart_name):
    message_wakeup = "1793,2,1,0"
    
    # if current state is STANDBY -> proceed with request
    state_battery_mode = read_data(
        "CAN_MSG_RX_LIVE", cart_name, "State_bat_mod"
    ).lower()
    mode_bat_only = read_data("CAN_MSG_RX_LIVE", cart_name, "Mode_Bat_only")

    if "standby" in state_battery_mode and "error" not in state_battery_mode:
        publish_message(message_wakeup)
        if check_feedback(cart_name, "WakeUp_OK"):
            return monitor_result("CAN_MSG_RX_LIVE", cart_name, "Mode_Bat_only", 1)

    # if current state is BAT_ONLY -> return true
    elif (
        "batok" in state_battery_mode
        and "error" not in state_battery_mode
        and mode_bat_only == 1
    ):
        return True

    else:
        return False


def mode_req_bat_only(cart_name):
    message_mode_req_bat_only = "1793,2,128,0"
    # if current state is ANY_STATE -> proceed with request
    # if current state is BAT_ONLY -> return true
    return True


def mode_req_standby(cart_name):
    message_mode_req_standby = "1793,2,16,0"
    # if current state is BAT_ONLY -> proceed with request
    # if current state is STANDBY -> return true
    # else -> return false
    return True


def mode_req_idle(cart_name):
    message_mode_req_idle = "1793,2,32,0"
    # if current state is BAT_ONLY -> proceed with request
    # if current state is IDLE -> return true
    # else -> return false
    return True


def mode_req_EV_AC_Charge(cart_name):
    message_mode_req_EV_AC_Charge = "1793,2,4,0"
    # if current state is IDLE -> proceed with request
    # if current state is EV_AC_Charge -> return true
    # else -> return false
    return True


def mode_req_EV_DC_Charge(cart_name):
    message_mode_req_EV_DC_Charge = "1793,2,2,0"
    # if current state is IDLE -> proceed with request
    # if current state is EV_DC_Charge -> return true
    # else -> return false
    return True


def mode_req_Bat_AC_Charge(cart_name):
    message_mode_req_Bat_AC_Charge = "1793,2,8,0"
    # if current state is IDLE -> proceed with request
    # if current state is Bat_AC_Charge -> return true
    # else -> return false
    return True


def ladeprozess_start(cart_name):
    message_unlock_request = "1793,2,64,0"  # not when EV_DC_Charge Ladeprozess Start
    message_plug_process_finished = "1793,2,0,1"
    # if current state is EV_AC_Charge / EV_DC_Charge / Bat_AC_Charge-> proceed with request
    # if current state is EV_AC_Charge / EV_DC_Charge / Bat_AC_Charge Ladeprozess -> return true
    # else -> return false
    return True


def ladeprozess_end(cart_name):
    message_mode_req_idle = "1793,2,32,0"
    message_plug_process_finished = "1793,2,0,1"
    # if current state is EV_AC_Charge / EV_DC_Charge / Bat_AC_Charge Ladeprozess-> proceed with request
    # if current state is BAT_ONLY-> return true
    # else -> return false
    return True


def mode_req_emergency_shutdown(cart_name):
    message = "1793,2,0,2"
    # if current state is ANY_STATE -> proceed with request
    # if current state is STANDBY -> return true
    return True
