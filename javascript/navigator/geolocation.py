__author__ = 'katharine'

import PyV8 as v8
import time
import requests
import pygeoip
import os.path


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
    def __init__(self, runtime):
        self.__runtime = runtime

    def _get_position(self, success, failure):
        try:
            resp = requests.get('http://ip.42.pl/raw')
            resp.raise_for_status()
            ip = resp.text
            gi = pygeoip.GeoIP('%s/GeoLiteCity.dat' % os.path.dirname(__file__))
            record = gi.record_by_addr(ip)
            if record is None:
                if callable(failure):
                    self.__runtime.enqueue(failure)
        except (requests.RequestException, pygeoip.GeoIPError):
            if callable(failure):
                self.__runtime.enqueue(failure)
        else:
            self.__runtime.enqueue(success, Position(Coordinates(record['longitude'], record['latitude'], 1000), int(time.time() * 1000)))

    def getCurrentPosition(self, success, failure=None, options=None):
        self.__runtime.group.spawn(self._get_position, success, failure)

    def watchPosition(self, success, failure=None, options=None):
        self.__runtime.group.spawn(self._get_position, success, failure)
        return 42

    def clearWatch(self, thing):
        pass
