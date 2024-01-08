#!/usr/bin/env python3
from server import CommunicationServicer

job_details = ""
def fetch_job(robot_name):
    server_obj = CommunicationServicer()
    job_success = server_obj.job_success_status
    
    if job_success:
       
        job_type = input("Enter job type: ")
        charger = input("Enter charger name: ")
        source_station = input("Enter source_station name: ")
        target_station = input("Enter target_station name: ")
        
        job_details = {
                    "job_type": job_type,
                    "robot_name": robot_name,
                    "charger": charger,
                    "source_station": source_station,
                    "target_station": target_station,
                    }
        print("----------------------------------------------")
       
    else:
        print("Previous job was unsuccessful!!")

    return job_details