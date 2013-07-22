try: import unittest2 as unittest
except ImportError: import unittest
from minimock import mock, restore, TraceTracker, assert_same_trace
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

        expected = "Called temp_alert.get_data('')\n" * 4
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

