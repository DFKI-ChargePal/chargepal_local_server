#!/usr/bin/env python3

def fetch_job(robot_name):
    job_details = {
                "job_type": "BRING_CHARGER",
                "robot_name": robot_name,
                "charger": "BAT_1",
                "source_station": "ADS_1",
                "target_station": "ADS_2",
                }
    return job_details