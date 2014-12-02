__author__ = 'katharine'

import PyV8 as v8
from geolocation import Geolocation


class Navigator(v8.JSClass):
    def __init__(self, group):
        self.geolocation = Geolocation(group)