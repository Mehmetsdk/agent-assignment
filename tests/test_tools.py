import json
import unittest

from src import tools


class ToolsTest(unittest.TestCase):
    def test_calendar_check(self):
        res = json.loads(tools.calendar_check("next week"))
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["available"])

    def test_search_service(self):
        res = json.loads(tools.search_service("coworking spaces in Warsaw"))
        self.assertEqual(res["status"], "success")
        self.assertGreaterEqual(len(res["results"]), 2)

    def test_booking_service(self):
        res = json.loads(tools.booking_service("dentist appointment"))
        self.assertEqual(res["status"], "success")
        self.assertIn("booking_ref", res)

    def test_reminder_create(self):
        res = json.loads(tools.reminder_create("dentist appointment tomorrow"))
        self.assertEqual(res["status"], "success")
        self.assertIn("message", res)


if __name__ == "__main__":
    unittest.main()
