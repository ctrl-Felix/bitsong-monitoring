from mongoengine import *

class Blocks(Document):
    height = LongField(required=True)
    time = DateTimeField(required=True)
    signed = ListField(required=True)
