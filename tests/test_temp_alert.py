try: import unittest2 as unittest
except ImportError: import unittest
import smtplib
import ConfigParser
from minimock import mock, restore, TraceTracker, assert_same_trace, Mock
from temp_alert import TempAlert
import temp_alert as orig_ta
from cStringIO import StringIO

class TestTempAlert(unittest.TestCase):
    def setUp(self):
        self.tt = TraceTracker()
        mock("orig_ta.urlopen", tracker=self.tt)


    def tearDown(self):
        restore()


    def test_get_data(self):
        "Test get_data()"
        temp_alert = TempAlert()
        mock("orig_ta.urlopen", returns=StringIO('{"test": "passed"}'),
             tracker=self.tt)

        self.assertEqual({'test': 'passed'}, temp_alert.get_data('test'))

        expected = "Called orig_ta.urlopen('http://localhost:8367/test')"
        assert_same_trace(self.tt, expected)


    def test_get_status(self):
        "Test get_status()"
        # Status is OK
        temp_alert = TempAlert()
        mock("temp_alert.get_data", returns={u'status': u'ok'}, tracker=self.tt)
        self.assertEqual('ok', temp_alert.get_status())

        # Status is ALARM
        mock("temp_alert.get_data", returns={u'status': u'alarm'}, tracker=self.tt)
        self.assertEqual('alarm', temp_alert.get_status())

        # Status is PANIC
        mock("temp_alert.get_data", returns={u'status': u'panic'}, tracker=self.tt)
        self.assertEqual('panic', temp_alert.get_status())

        # And test error handling
        mock("temp_alert.get_data",
             returns={u'error': u'failed reading sensors'}, tracker=self.tt)
        self.assertEqual('error reading from server', temp_alert.get_status())

        expected = "Called temp_alert.get_data('status')\n" * 4
        assert_same_trace(self.tt, expected)


    def test_get_available_sensors(self):
        "Test get_available_sensors()"
        temp_alert = TempAlert()
        mock("temp_alert.get_data", returns={u'sensors': [u'first', u'second']},
             tracker=self.tt)
        self.assertEqual(['first', 'second'], temp_alert.get_available_sensors())

        expected = "Called temp_alert.get_data('available')"
        assert_same_trace(self.tt, expected)


    def test_get_sensor(self):
        "Test get_sensor()"
        temp_alert = TempAlert()

        # Everything is fine
        mock("temp_alert.get_data",
             returns={u'temp':23.45, u'alarm': False, u'panic': False},
             tracker=self.tt)
        sensor = temp_alert.get_sensor('foo')
        self.assertAlmostEqual(23.45, sensor['temp'])
        self.assertFalse(sensor['alarm'])
        self.assertFalse(sensor['panic'])

        # Alarm state
        mock("temp_alert.get_data",
             returns={u'temp':23.45, u'alarm': True, u'panic': False},
             tracker=self.tt)
        sensor = temp_alert.get_sensor('foo')
        self.assertAlmostEqual(23.45, sensor['temp'])
        self.assertTrue(sensor['alarm'])
        self.assertFalse(sensor['panic'])

        # Panic state
        mock("temp_alert.get_data",
             returns={u'temp':23.45, u'alarm': True, u'panic': True},
             tracker=self.tt)
        sensor = temp_alert.get_sensor('foo')
        self.assertAlmostEqual(23.45, sensor['temp'])
        self.assertTrue(sensor['alarm'])
        self.assertTrue(sensor['panic'])

        expected = "Called temp_alert.get_data('foo')\n" * 3
        assert_same_trace(self.tt, expected)


    def test_find_problematic_sensors(self):
        """Test find_problematic_sensors()"""
        temp_alert = TempAlert()
        returns = [
            {'sensors': ['fine01', 'alarm', 'fine02', 'panic']},
            {'temp': 23.42, 'alarm': False, 'panic': False},
            {'temp': 23.42, 'alarm': True, 'panic': False},
            {'temp': 23.42, 'alarm': False, 'panic': False},
            {'temp': 42.23, 'alarm': False, 'panic': True},
        ]
        mock("temp_alert.get_data", returns_iter=returns, tracker=self.tt)

        results = temp_alert.find_problematic_sensors()
        self.assertEqual({'alarm': 23.42, 'panic': 42.23}, results)

        expected = "Called temp_alert.get_data('available')\n"
        expected += "Called temp_alert.get_data('fine01')\n"
        expected += "Called temp_alert.get_data('alarm')\n"
        expected += "Called temp_alert.get_data('fine02')\n"
        expected += "Called temp_alert.get_data('panic')\n"


class TestSendAlertMail(unittest.TestCase):
    def setUp(self):
        self.tt = TraceTracker()
        mock("smtplib.SMTP", returns=Mock('smtp_conn', tracker=self.tt),
             tracker=self.tt)
        self.config = ConfigParser.SafeConfigParser()
        self.config.add_section('email')
        self.config.set('email', 'host', 'localhost')
        self.config.set('email', 'sender', 'sally@example.com')
        self.config.set('email', 'recipients',
                        'alice@example.com, bob@example.com')

    def tearDown(self):
        restore()

    def test_send_email(self):
        "Test send_email()"
        expected = r'''Called smtplib.SMTP('localhost')
Called smtp_conn.sendmail(
    'sally@example.com',
    ['alice@example.com', 'bob@example.com'],
    'From: sally@example.com\nTo: alice@example.com, bob@example.com\nSubject: Temperature Alert - Status: alarm\n\nThe following sensors are in alarm or panic state:\nSensor\tTemperature\nfoo\t23.42\nbar\t42.23\n\nSincerely,\ntemp-alert\n')
Called smtp_conn.quit()'''
        template = orig_ta.build_alert_mail('alarm', {'foo': 23.42, 'bar': 42.23})
        orig_ta.send_email(self.config, template)
        assert_same_trace(self.tt, expected)


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.tt = TraceTracker()
        mock("smtplib.SMTP", returns=Mock('smtp_conn', tracker=self.tt),
             tracker=self.tt)
        self.config = ConfigParser.SafeConfigParser()
        self.config.add_section('email')
        self.config.set('email', 'host', 'localhost')
        self.config.set('email', 'sender', 'sally@example.com')
        self.config.set('email', 'recipients',
                        'alice@example.com, bob@example.com')

        mock("orig_ta.load_config", returns=self.config, tracker=self.tt)
        mock_alert = Mock('TempAlert', tracker=self.tt)
        mock_alert.get_status = Mock('get_status', returns='alarm',
                tracker=self.tt)
        mock_alert.find_problematic_sensors = Mock('find_problematic_sensors',
                returns={'foo': 23.42, 'bar': 42.23}, tracker=self.tt)
        mock("orig_ta.TempAlert", returns=mock_alert)

    def tearDown(self):
        restore()

    def test_main(self):
        "Test main()"
        expected = r'''Called orig_ta.load_config()
Called get_status()
Called find_problematic_sensors()
Called smtplib.SMTP('localhost')
Called smtp_conn.sendmail(
    'sally@example.com',
    ['alice@example.com', 'bob@example.com'],
    'From: sally@example.com\nTo: alice@example.com, bob@example.com\nSubject: Temperature Alert - Status: alarm\n\nThe following sensors are in alarm or panic state:\nSensor\tTemperature\nfoo\t23.42\nbar\t42.23\n\nSincerely,\ntemp-alert\n')
Called smtp_conn.quit()'''

        orig_ta.main()
        assert_same_trace(self.tt, expected)
