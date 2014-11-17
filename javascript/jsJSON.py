__author__ = 'katharine'

import PyV8 as v8
import json


class JSON(v8.JSClass):
    @staticmethod
    def parse(string):
        return json.loads(string)

    @staticmethod
    def stringify(obj):
        return json.dumps(obj)
