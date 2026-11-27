# Copyright 2020 Google LLC
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

import os
import shutil
import sys
import tempfile
import unittest

# Ensure the process module can be imported
MODULE_DIR = os.path.dirname(__file__)
sys.path.insert(0, MODULE_DIR)
from process import NCESPrivateSchool

# Define paths for test data and expected outputs
TEST_DATA_DIR = os.path.join(MODULE_DIR, "test_data", "sample_input")
EXPECTED_OUTPUT_DIR = os.path.join(MODULE_DIR, "test_data", "sample_output")


class TestProcess(unittest.TestCase):
    """
    Tests the NCESPrivateSchool processing script.

    This test runs the processor on sample input data within a temporary
    directory and compares the generated files against the expected outputs.
    """

    def setUp(self):
        """
        Set up the test environment before each test method runs.
        This is the correct place to prepare resources, not __init__.
        """
        import unittest.mock
        self.patcher = unittest.mock.patch(
            'common.us_education.dc_api_is_defined_dcid')
        self.mock_dc_api = self.patcher.start()

        def mock_dc_api_side_effect(dcids, *args, **kwargs):
            valid_dcids = set()
            golden_place = os.path.join(
                EXPECTED_OUTPUT_DIR, "us_nces_demographics_private_place.csv")
            if os.path.exists(golden_place):
                with open(golden_place, 'r', encoding='utf-8') as f:
                    for line in f:
                        import re
                        valid_dcids.update(
                            re.findall(r'(zip/\d{5}|geoId/\d{2,5})', line))

            result = {}
            for dcid in dcids:
                if str(dcid).startswith('zip/') or str(dcid).startswith(
                        'geoId/'):
                    result[dcid] = dcid in valid_dcids
                else:
                    result[dcid] = True
            return result

        self.mock_dc_api.side_effect = mock_dc_api_side_effect

        # Create a temporary directory to store generated files for one test run
        self.tmp_dir = tempfile.mkdtemp()

        # Define paths for all input and output files
        input_files = [
            os.path.join(TEST_DATA_DIR, f) for f in os.listdir(TEST_DATA_DIR)
        ]
        cleaned_csv_path = os.path.join(self.tmp_dir, "test_private_school.csv")
        mcf_path = os.path.join(self.tmp_dir, "test_private_school.mcf")
        tmcf_path = os.path.join(self.tmp_dir, "test_private_school.tmcf")
        csv_path_place = os.path.join(self.tmp_dir,
                                      "test_private_school_place.csv")
        tmcf_path_place = os.path.join(self.tmp_dir,
                                       "test_private_school_place.tmcf")
        dup_csv_path_place = os.path.join(self.tmp_dir,
                                          "test_private_school_place_dup.csv")

        # Instantiate and run the processor to generate the files
        loader = NCESPrivateSchool(input_files, cleaned_csv_path, mcf_path,
                                   tmcf_path, csv_path_place,
                                   dup_csv_path_place, tmcf_path_place)
        loader.generate_csv()
        loader.generate_mcf()
        loader.generate_tmcf()

        # Read the contents of the generated files into memory for comparison
        with open(cleaned_csv_path, "r", encoding="utf-8-sig") as f:
            self.actual_csv_data = f.read()
        with open(mcf_path, "r", encoding="UTF-8") as f:
            self.actual_mcf_data = f.read()
        with open(tmcf_path, "r", encoding="UTF-8") as f:
            self.actual_tmcf_data = f.read()
        with open(csv_path_place, "r", encoding="utf-8-sig") as f:
            self.actual_csv_place = f.read()
        with open(tmcf_path_place, "r", encoding="UTF-8") as f:
            self.actual_tmcf_place = f.read()

    def tearDown(self):
        """
        Clean up the test environment after each test method runs.
        """
        self.patcher.stop()
        # Reliably remove the temporary directory and all its contents
        shutil.rmtree(self.tmp_dir)

    def test_csv_files(self):
        """
        Tests that the generated CSV files match the expected output.
        """

        def sort_csv_content(csv_content):
            lines = csv_content.strip().split('\n')
            if not lines:
                return ""
            return '\n'.join([lines[0]] + sorted(lines[1:]))

        # Compare the main CSV file
        with open(os.path.join(EXPECTED_OUTPUT_DIR,
                               "us_nces_demographics_private_school.csv"),
                  "r",
                  encoding="utf-8") as f:
            expected_csv_data = f.read()
        self.assertEqual(sort_csv_content(self.actual_csv_data),
                         sort_csv_content(expected_csv_data))

        # Compare the place CSV file
        with open(os.path.join(EXPECTED_OUTPUT_DIR,
                               "us_nces_demographics_private_place.csv"),
                  "r",
                  encoding="utf-8") as f:
            expected_csv_place = f.read()
        self.assertEqual(sort_csv_content(self.actual_csv_place),
                         sort_csv_content(expected_csv_place))

    def test_mcf_and_tmcf_files(self):
        """
        Tests that the generated MCF and TMCF files match the expected output.
        """
        # Compare MCF file
        with open(os.path.join(EXPECTED_OUTPUT_DIR,
                               "us_nces_demographics_private_school.mcf"),
                  "r",
                  encoding="UTF-8") as f:
            expected_mcf_data = f.read()
        self.assertEqual(self.actual_mcf_data.strip(),
                         expected_mcf_data.strip())

        # Compare main TMCF file
        with open(os.path.join(EXPECTED_OUTPUT_DIR,
                               "us_nces_demographics_private_school.tmcf"),
                  "r",
                  encoding="UTF-8") as f:
            expected_tmcf_data = f.read()
        self.assertEqual(self.actual_tmcf_data.strip(),
                         expected_tmcf_data.strip())

        # Compare place TMCF file
        with open(os.path.join(EXPECTED_OUTPUT_DIR,
                               "us_nces_demographics_private_place.tmcf"),
                  "r",
                  encoding="UTF-8") as f:
            expected_tmcf_place = f.read()
        self.assertEqual(self.actual_tmcf_place.strip(),
                         expected_tmcf_place.strip())


if __name__ == '__main__':
    unittest.main()
