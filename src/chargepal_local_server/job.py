from chargepal_local_server.server import CommunicationServicer


def fetch_job(robot_name: str) -> str:
    server_obj = CommunicationServicer()
    job_success = server_obj.job_success_status
    job_details = ""

    if job_success:
        job_type = input("Enter job type: ")
        cart = input("Enter cart name: ")
        source_station = input("Enter source_station name: ")
        target_station = input("Enter target_station name: ")

        job_details = {
            "job_type": job_type,
            "robot_name": robot_name,
            "cart": cart,
            "source_station": source_station,
            "target_station": target_station,
        }
        print("----------------------------------------------")

    else:
        print("Previous job was unsuccessful!!")

    return job_details
