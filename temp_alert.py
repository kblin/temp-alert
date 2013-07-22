#!/usr/bin/env python
# vim:set fileencoding=utf8 :

import json
import sys
import smtplib
import ConfigParser
from os import path
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


def load_config():
    "Load config file"
    config = ConfigParser.SafeConfigParser()
    config.read(path.expanduser("~/.temp_alertrc"))
    return config


def send_email(config, status, sensors):
    "Send an alert email"
    template = """From: %(sender)s
To: %(recipients)s
Subject: Temperature Alert - Status: %(status)s

The following sensors are in alarm or panic state:
Sensor\tTemperature
%(sensors)s

Sincerely,
temp-alert
"""
    contents = dict(config.items('email'))
    if not 'sender' in contents:
        raise ValueError("No sender in configfile")
    if not 'recipients' in contents:
        raise ValueError("No recipients in configfile")
    if not 'host' in contents:
        raise ValueError("No mail server set in configfile")

    contents['status'] = status

    sensor_text = ""
    for name in sensors:
        sensor_text += "%s\t%0.2f\n" % (name, sensors[name])
    sensor_text = sensor_text[:-1]
    contents['sensors'] = sensor_text

    message = template % contents

    recipients = map(lambda x: x.strip(), contents['recipients'].split(','))

    conn = smtplib.SMTP(contents['host'])
    conn.sendmail(contents['sender'], recipients, message)
    conn.quit()


def main():
    # defaults
    host = 'localhost'
    port = 8367
    config = load_config()

    # override defaults from config
    if config.has_section('temp-monitor') and \
       config.has_option('temp-monitor', 'host'):
        host = config.get('temp-monitor', 'host')
    if config.has_section('temp-monitor') and \
       config.has_option('temp-monitor', 'port'):
        port = config.getint('temp-monitor', 'port')
    ta = TempAlert(host=host, port=port)

    status = ta.get_status()
    if status == "ok":
        sys.exit(0)

    send_email(config, status, ta.find_problematic_sensors())


if __name__ == "__main__":
    main()
