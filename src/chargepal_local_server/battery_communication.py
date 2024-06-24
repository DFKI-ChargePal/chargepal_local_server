#!/usr/bin/env python3
import time

def input_check(ip):
    if ip == "y" or ip == "Y":
        return True
    else:
        return False
    
def wakeup(cart_name):
    ip = input(f"Wakeup request for {cart_name} (y/n)")
    return input_check(ip)
def mode_req_standby(cart_name):
    ip = input(f"Mode request standby for {cart_name} (y/n)")
    return input_check(ip)
def mode_req_idle(cart_name):
    ip = input(f"Mode request idle for {cart_name} (y/n)")
    return input_check(ip)
def mode_req_EV_AC_Charge(cart_name):
    ip = input(f"Mode request EV_AC_Charge for {cart_name} (y/n)")
    return input_check(ip)
def mode_req_EV_DC_Charge(cart_name):
    ip = input(f"Mode request EV_DC_Charge for {cart_name} (y/n)")
    return input_check(ip)
def mode_req_Bat_AC_Charge(cart_name):
    ip = input(f"Mode request Bat_AC_Charge for {cart_name} (y/n)")
    return input_check(ip)
def ladeprozess_start(cart_name):
    ip = input(f"Ladeprozess start for {cart_name} (y/n)")
    return input_check(ip)
def ladeprozess_end(cart_name):
    ip = input(f"Ladeprozess end for {cart_name} (y/n)")
    return input_check(ip)
