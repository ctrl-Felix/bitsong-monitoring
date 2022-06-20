import datetime

from mongoengine import *

class Endpoints(Document):
    time = DateTimeField(required=True, default=datetime.datetime.utcnow)
    report = DictField(required=True)
