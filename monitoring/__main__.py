import os
import threading
import time

from mongoengine import connect

from monitoring import *
from monitoring import endpoints, validators
from database.Endpoints import Endpoints

connect(host=os.getenv("MONGO"), db="delegationdao")


def startUptimeMonitoring() -> None:
    endpointscls = endpoints.Endpoints()
    while True:
        report = endpointscls.createUptimeReport()
        db = Endpoints(
            report=report
        )
        db.save()
        logging.info("Uptime Report stored to database")
        time.sleep(60)


logging.info("Starting Uptime Monitoring")
t = threading.Thread(target=startUptimeMonitoring, daemon=True)
t.start()

c = validators.Validators()
c.start()
