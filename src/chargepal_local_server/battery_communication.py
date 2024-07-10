from typing import Dict, Optional, Union
from datetime import datetime
import mysql.connector
import paho.mqtt.client as mqtt
from chargepal_local_server.access_ldb import MySQLAccess

feedback_receive_timeout = 60
battery_live_monitor_timeout = 180


class UpdateManager:
    def __init__(self, battery_ids: Dict[str, str]) -> None:
        assert len(set(battery_ids.keys())) == len(set(battery_ids.values()))
        self.battery_names = {
            battery_id: cart_name for cart_name, battery_id in battery_ids.items()
        }
        self.battery_states: Dict[str, Optional[str]] = {
            cart_name: None for cart_name in battery_ids.keys()
        }
        self.last_time = datetime.min

    def tick(self) -> Dict[str, str]:
        """
        Return from CAN_MSG_RX_LIVE in lsv_db a dict of cart_names and battery states
        for which last_change is greater than last time.
        """
        sql_operation = f"SELECT Battry_ID, State_bat_mod FROM CAN_MSG_RX_LIVE WHERE last_change >= '{self.last_time}';"
        self.last_time = datetime.now()
        updated_states: Dict[str, str] = {}
        try:
            with MySQLAccess() as cursor:
                cursor.execute(sql_operation)
                for battery_id, state in cursor.fetchall():
                    updated_states[self.battery_names[battery_id]] = state
        except mysql.connector.errors.Error:
            pass
        self.battery_states.update(updated_states)
        return updated_states


def publish_message(cart_name: str, message: str):
    client = mqtt.Client()
    client.connect("192.168.185.25", 1883, 60)
    client.publish(cart_name, message)
    client.disconnect()


def read_data(table_name: str, battery_name: str, column_name: str) -> Union[str, int]:
    sql = MySQLAccess()
    query = f"SELECT {column_name} FROM {table_name} WHERE Battry_ID = %s"
    sql.cursor.execute(query, (battery_name,))
    result = sql.cursor.fetchone()
    return result[0]


def check_feedback(cart_name: str, msg_to_check: str) -> bool:
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


def monitor_result(
    table_name: str,
    battery_name: str,
    column_name: str,
    expected_result: Union[str, int],
) -> bool:
    result_success = False
    time_passed = 0
    monitor_result_start_time = datetime.now()
    while time_passed < battery_live_monitor_timeout:
        if expected_result == read_data(table_name, battery_name, column_name):
            result_success = True
        else:
            time_passed = (datetime.now() - monitor_result_start_time).total_seconds()

    return result_success


def wakeup(cart_name: str) -> bool:
    message_wakeup = "1793,2,1,0"
    state_battery_mode = read_data(
        "CAN_MSG_RX_LIVE", cart_name, "State_bat_mod"
    ).lower()
    mode_bat_only = read_data("CAN_MSG_RX_LIVE", cart_name, "Mode_Bat_only")
    success = False
    # if current state is STANDBY -> proceed with request
    if "batok" in state_battery_mode and "error" not in state_battery_mode and mode_bat_only==0:
        publish_message(cart_name, message_wakeup)
        if check_feedback(cart_name, "WakeUp_OK"):
            success = monitor_result("CAN_MSG_RX_LIVE", cart_name, "Mode_Bat_only", 1)

    # if current state is BAT_ONLY -> return true
    elif (
        "batok" in state_battery_mode
        and "error" not in state_battery_mode
        and mode_bat_only == 1
    ):
        success = True

    return success


def mode_req_bat_only(cart_name: str) -> bool:
    message_mode_req_bat_only = "1793,2,128,0"
    # if current state is ANY_STATE -> proceed with request
    # if current state is BAT_ONLY -> return true
    return True


def mode_req_standby(cart_name: str) -> bool:
    message_mode_req_standby = "1793,2,16,0"
    state_battery_mode = read_data(
        "CAN_MSG_RX_LIVE", cart_name, "State_bat_mod"
    ).lower()
    mode_bat_only = read_data("CAN_MSG_RX_LIVE", cart_name, "Mode_Bat_only")
    success = False
    # if current state is STANDBY -> return true
    if (
        "standby" in state_battery_mode and "error" not in state_battery_mode
    ):  ##verify how to know if standby is reached?
        success = True

    # if current state is BAT_ONLY -> proceed with request
    elif "error" not in state_battery_mode and mode_bat_only == 1:
        publish_message(cart_name, message_mode_req_standby)
        if check_feedback(cart_name, "Standby_OK"):
            success = monitor_result(
                "CAN_MSG_RX_LIVE", cart_name, "Mode_Bat_only", 1
            )  ##verify how to know if standby is reached?

    # else -> return false
    return success


def mode_req_idle(cart_name: str) -> bool:
    message_mode_req_idle = "1793,2,32,0"
    state_battery_mode = read_data(
        "CAN_MSG_RX_LIVE", cart_name, "State_bat_mod"
    ).lower()
    flg_modus = read_data("CAN_MSG_RX_LIVE", cart_name, "Flag_Modus").lower()
    mode_bat_only = read_data("CAN_MSG_RX_LIVE", cart_name, "Mode_Bat_only")
    success = False
    # if current state is IDLE -> return true
    if "batok" in state_battery_mode and "flag_idle" in flg_modus:
        success = True

    # if current state is BAT_ONLY -> proceed with request
    elif "error" not in state_battery_mode and mode_bat_only == 1:
        publish_message(cart_name, message_mode_req_idle)
        if check_feedback(cart_name, "Mode_request_idle_OK"):
            success = monitor_result(
                "CAN_MSG_RX_LIVE", cart_name, "Flag_Modus", "Flag_idle"
            )

    # else -> return false
    return success


def mode_req_EV_AC_Charge(cart_name: str) -> bool:
    message_mode_req_EV_AC_Charge = "1793,2,4,0"
    state_battery_mode = read_data(
        "CAN_MSG_RX_LIVE", cart_name, "State_bat_mod"
    ).lower()
    flg_modus = read_data("CAN_MSG_RX_LIVE", cart_name, "Flag_Modus").lower()
    success = False

    # if current state is EV_AC_Charge -> return true
    if "error" not in state_battery_mode and "flag_ev_ac_charge" in flg_modus:
        success = True

    # if current state is IDLE -> proceed with request
    elif "error" not in state_battery_mode and "flag_idle" in flg_modus:
        publish_message(cart_name, message_mode_req_EV_AC_Charge)
        if check_feedback(cart_name, "EV_Ac_Charge_OK"):
            success = monitor_result(
                "CAN_MSG_RX_LIVE", cart_name, "Flag_Modus", "Flag_EV_AC_Charge"
            )

    # else -> return false
    return success


def mode_req_EV_DC_Charge(cart_name: str) -> bool:
    message_mode_req_EV_DC_Charge = "1793,2,2,0"
    state_battery_mode = read_data(
        "CAN_MSG_RX_LIVE", cart_name, "State_bat_mod"
    ).lower()
    flg_modus = read_data("CAN_MSG_RX_LIVE", cart_name, "Flag_Modus").lower()
    success = False

    # if current state is EV_DC_Charge -> return true
    if "error" not in state_battery_mode and "flag_ev_dc_charge" in flg_modus:
        success = True

    # if current state is IDLE -> proceed with request
    elif "error" not in state_battery_mode and "flag_idle" in flg_modus:
        publish_message(cart_name, message_mode_req_EV_DC_Charge)
        if check_feedback(cart_name, "EV_Dc_Charge_OK"):
            success = monitor_result(
                "CAN_MSG_RX_LIVE", cart_name, "Flag_Modus", "Flag_EV_DC_Charge"
            )

    # else -> return false
    return success


def mode_req_Bat_AC_Charge(cart_name: str) -> bool:
    message_mode_req_Bat_AC_Charge = "1793,2,8,0"
    state_battery_mode = read_data(
        "CAN_MSG_RX_LIVE", cart_name, "State_bat_mod"
    ).lower()
    flg_modus = read_data("CAN_MSG_RX_LIVE", cart_name, "Flag_Modus").lower()
    success = False
    # if current state is Bat_AC_Charge -> return true
    if "error" not in state_battery_mode and "flag_bat_ac_charge" in flg_modus:
        success = True

    # if current state is IDLE -> proceed with request
    elif "error" not in state_battery_mode and "flag_idle" in flg_modus:
        publish_message(cart_name, message_mode_req_Bat_AC_Charge)
        if check_feedback(cart_name, "Bat_Ac_Charge_OK"):
            success = monitor_result(
                "CAN_MSG_RX_LIVE", cart_name, "Flag_Modus", "Flag_Bat_AC_Charge"
            )

    # else -> return false
    return success


def ladeprozess_start(cart_name: str, station_name: str, charging_type: str) -> bool:
    flg_modus = read_data("CAN_MSG_RX_LIVE", cart_name, "Flag_Modus").lower()
    state_battery_mode = read_data(
        "CAN_MSG_RX_LIVE", cart_name, "State_bat_mod"
    ).lower()
    success = False
    if (
        "flag_ev_ac_charge" in flg_modus
        or "flag_ev_dc_charge" in flg_modus
        or "flag_bat_ac_charge" in flg_modus
        and "enable" in state_battery_mode
    ):
        if "flag_ev_dc_charge" not in flg_modus:
            message_unlock_request = (
                "1793,2,64,0"  # not when EV_DC_Charge Ladeprozess Start
            )
            publish_message(cart_name, message_unlock_request)
            if check_feedback(cart_name, "Unlock_request_OK"):
                if not monitor_plug_unlock(cart_name, station_name):
                    return success

        message_plug_process_finished = "1793,2,0,1"
        publish_message(cart_name, message_plug_process_finished)
        if check_feedback(cart_name, "PlugProcessFinished_Received"):
            if "BCS" in station_name:
                success = monitor_result(
                    "CAN_MSG_RX_LIVE", cart_name, "Flag_Modus", "Flag_Bat_AC_Charge"
                )
            elif "ADS" in station_name:
                if charging_type.lower() == "ac":
                    success = monitor_result(
                        "CAN_MSG_RX_LIVE", cart_name, "Flag_Modus", "Flag_EV_AC_Charge"
                    )
                else:
                    success = monitor_result(
                        "CAN_MSG_RX_LIVE", cart_name, "Flag_Modus", "Flag_EV_DC_Charge"
                    )

    return success


def monitor_plug_unlock(cart_name: str, station_name: str) -> bool:
    if "ADS" in station_name:
        return monitor_result("CAN_MSG_RX_LIVE", cart_name, "AC_Car_inlet_UNLOCKED", 1)
    elif "BCS" in station_name:
        return monitor_result(
            "CAN_MSG_RX_LIVE", cart_name, "AC_Charger_inlet_UNLOCKED", 1
        )


def ladeprozess_end(cart_name: str, station_name: str, charging_type: str) -> bool:
    flg_modus = read_data("CAN_MSG_RX_LIVE", cart_name, "Flag_Modus").lower()
    unlock_state = monitor_plug_unlock(cart_name, station_name)
    success = False

    # if current state is EV_AC_Charge / EV_DC_Charge / Bat_AC_Charge Ladeprozess-> proceed with request
    if (
        "flag_ev_ac_charge" in flg_modus
        or "flag_ev_dc_charge" in flg_modus
        or "flag_bat_ac_charge" in flg_modus
    ):
        if not unlock_state:
            message_mode_req_idle = "1793,2,32,0"
            publish_message(cart_name, message_mode_req_idle)
            if check_feedback(cart_name, "Mode_request_idle_OK"):
                if not monitor_plug_unlock(cart_name, station_name):
                    return success
            else:
                return success

        message_plug_process_finished = "1793,2,0,1"
        publish_message(cart_name, message_plug_process_finished)
        if check_feedback(cart_name, "PlugProcessFinished_Received"):
            success = monitor_result("CAN_MSG_RX_LIVE", cart_name, "Mode_Bat_only", 1)

    # if current state is BAT_ONLY-> return true
    # else -> return false
    return success


def mode_req_emergency_shutdown(cart_name):
    message = "1793,2,0,2"
    # if current state is ANY_STATE -> proceed with request
    # if current state is STANDBY -> return true
    return True
