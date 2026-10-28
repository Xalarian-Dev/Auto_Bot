"""Test de infer_region (scout/sources/base.py). Lancer : python -m unittest discover -s tests"""

import unittest

from scout.models import Region
from scout.sources.base import infer_region


class InferRegionTest(unittest.TestCase):
    def test_short_code_is_not_found_inside_words(self):
        self.assertEqual(infer_region("", "Vienna, Austria"), Region.OTHER)
        self.assertEqual(infer_region("", "Cyprus"), Region.OTHER)
        self.assertEqual(infer_region("", "Brussels"), Region.OTHER)

    def test_north_america_still_detected(self):
        self.assertEqual(infer_region("", "Washington, US"), Region.NORTH_AMERICA)
        self.assertEqual(infer_region("", "USA"), Region.NORTH_AMERICA)
        self.assertEqual(infer_region("United States", "New York"), Region.NORTH_AMERICA)

    def test_apac_unchanged(self):
        self.assertEqual(infer_region("", "Singapore"), Region.APAC)
        self.assertEqual(infer_region("Australia", "Sydney"), Region.APAC)
        self.assertEqual(infer_region("", "Bangkok, Thailand"), Region.APAC)


if __name__ == "__main__":
    unittest.main()
