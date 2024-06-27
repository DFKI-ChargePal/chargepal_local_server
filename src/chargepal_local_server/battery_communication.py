#!/usr/bin/env python3
import subprocess

def run_command_line(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)
    print("return code:", result.returncode)
    
def wakeup(cart_name):
    #if current state is STANDBY -> proceed with request
    #if current state is BAT_ONLY -> return true
    #else -> return false
    return True
def mode_req_bat_only(cart_name):
    #if current state is ANY_STATE -> proceed with request
    #if current state is BAT_ONLY -> return true
    ip = input(f"Mode request standby for {cart_name} (y/n)")
def mode_req_standby(cart_name):
    #if current state is BAT_ONLY -> proceed with request
    #if current state is STANDBY -> return true
    #else -> return false
    return True
def mode_req_idle(cart_name):
    #if current state is BAT_ONLY -> proceed with request
    #if current state is IDLE -> return true
    #else -> return false
    return True
def mode_req_EV_AC_Charge(cart_name):
    #if current state is IDLE -> proceed with request
    #if current state is EV_AC_Charge -> return true
    #else -> return false
    return True
def mode_req_EV_DC_Charge(cart_name):
    #if current state is IDLE -> proceed with request
    #if current state is EV_DC_Charge -> return true
    #else -> return false
    return True
def mode_req_Bat_AC_Charge(cart_name):
    #if current state is IDLE -> proceed with request
    #if current state is Bat_AC_Charge -> return true
    #else -> return false
    return True
def ladeprozess_start(cart_name):
    #if current state is EV_AC_Charge / EV_DC_Charge / Bat_AC_Charge-> proceed with request
    #if current state is EV_AC_Charge / EV_DC_Charge / Bat_AC_Charge Ladeprozess -> return true
    #else -> return false
    return True
def ladeprozess_end(cart_name):
    #if current state is EV_AC_Charge / EV_DC_Charge / Bat_AC_Charge Ladeprozess-> proceed with request
    #if current state is BAT_ONLY-> return true
    #else -> return false
    return True
def mode_req_emergency_shutdown(cart_name):
    #if current state is ANY_STATE -> proceed with request
    #if current state is STANDBY -> return true
    return True
