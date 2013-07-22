#!/usr/bin/env python
# vim:set fileencoding=utf8 :

import json
from urllib2 import urlopen

class TempAlert(object):
    """A class that bundles all the methods for dealing with the
    rpi-temp-monitor web pages and handle alerting users
    """
    def __init__(self, host="localhost", port=8367):
        self.host = host
        self.port = port


    def get_data(self, page):
        """Get JSON data from server and return a python data structure"""
        handle = urlopen("http://%s:%s/%s" % (self.host, self.port, page))
        data = json.loads(handle.read())
        return data


    def get_status(self):
        """Get the status of the sensors"""
        status = self.get_data('')
        if 'status' not in status:
            return 'error reading from server'
        return status['status']


    def get_available_sensors(self):
        """Get a list of available sensors"""
        sensors = self.get_data('available')
        if 'sensors' not in sensors:
            return []
        return sensors['sensors']


    def get_sensor(self, name):
        """Get data from a specific sensor"""
        return self.get_data(name)


    def find_problematic_sensors(self):
        """Get the sensors that are in alarm or panic state"""
        problematic = {}
        for sensor in self.get_available_sensors():
            data = self.get_sensor(sensor)
            if data['panic'] or data['alarm']:
                problematic[sensor] = data['temp']

        return problematic


def main():
    ta = TempAlert()
    status = ta.get_status()
    print status


if __name__ == "__main__":
    main()