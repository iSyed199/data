# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
'''
Unit tests for preprocess_gpcc_spi.py
Usage: python -m unittest discover -v -s ../ -p "preprocess_gpcc_spi_test.py"
'''
import unittest
from .preprocess_gpcc_spi import preprocess_one
import os
import tempfile
import filecmp
from dataclasses import dataclass
import pandas as pd
from . import preprocess_gpcc_spi

# module_dir is the path to where this test is running from.
module_dir = os.path.dirname(__file__)


@dataclass
class TestCase:
    input: str
    expected: str
    start_date: str
    end_date: str


class GPCCSPIPreprocessTest(unittest.TestCase):

    def test_preprocess(self):

        test_cases = [
            TestCase(input=os.path.join(module_dir,
                                        'testdata/gpcc_spi_pearson_12.nc'),
                     start_date='1988-01-01',
                     end_date='1988-12-01',
                     expected=os.path.join(
                         module_dir,
                         'testdata/expected_gpcc_spi_pearson_12.csv')),
            TestCase(input=os.path.join(module_dir,
                                        'testdata/gpcc_spi_pearson_72.nc'),
                     start_date='1988-01-01',
                     end_date='1988-12-01',
                     expected=os.path.join(
                         module_dir,
                         'testdata/expected_gpcc_spi_pearson_72.csv'))
        ]

        for test_case in test_cases:
            with tempfile.TemporaryDirectory() as tmp_dir:
                output_path = preprocess_one(test_case.start_date,
                                             test_case.end_date,
                                             test_case.input, tmp_dir)
                self.assertTrue(filecmp.cmp(output_path, test_case.expected))

    def test_to_one_degree_grid_place(self):
        # Test case 1: Positive lat/lon
        latlon_series_1 = pd.Series({'lat': 37.5, 'lon': 242.5})
        expected_1 = 'grid_1/37_-118'
        self.assertEqual(
            preprocess_gpcc_spi.to_one_degree_grid_place(latlon_series_1),
            expected_1)

        # Test case 2: Negative lat/lon
        latlon_series_2 = pd.Series({'lat': -10.5, 'lon': 10.5})
        expected_2 = 'grid_1/-11_10'
        self.assertEqual(
            preprocess_gpcc_spi.to_one_degree_grid_place(latlon_series_2),
            expected_2)

        # Test case 3: Lat/lon at boundary (e.g., 0, 180, 360)
        latlon_series_3 = pd.Series({'lat': 0.0, 'lon': 180.0})
        expected_3 = 'grid_1/0_-180'
        self.assertEqual(
            preprocess_gpcc_spi.to_one_degree_grid_place(latlon_series_3),
            expected_3)

        # Test case 4: Lat/lon at 359.9 (just before 360)
        latlon_series_4 = pd.Series({'lat': 1.0, 'lon': 359.9})
        expected_4 = 'grid_1/1_-1'
        self.assertEqual(
            preprocess_gpcc_spi.to_one_degree_grid_place(latlon_series_4),
            expected_4)


if __name__ == '__main__':
    unittest.main()
