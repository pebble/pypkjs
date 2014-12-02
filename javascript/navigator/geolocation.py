__author__ = 'katharine'

import PyV8 as v8
import time

class Position(v8.JSClass):
    def __init__(self, coords, timestamp):
        self.coords = coords
        self.timestamp = timestamp


class Coordinates(v8.JSClass):
    def __init__(self, long, lat, accuracy):
        self.longitude = long
        self.latitude = lat
        self.accuracy = accuracy



class Geolocation(v8.JSClass):
    def __init__(self, group):
        self.__group = group

    def getCurrentPosition(self, success, failure=None, options=None):
        self.__group.spawn(success, Position(Coordinates(37.4401251, -122.1583327, 10), int(time.time() * 1000)))

    def watchPosition(self, success, failure=None, options=None):
        self.__group.spawn(success, Position(Coordinates(37.4401251, -122.1583327, 10), int(time.time() * 1000)))
        return 42

    def clearWatch(self, thing):
        pass
