import unittest
import os
import pandas as pd
import tempfile
import shutil
from io import StringIO
import logging

# Import the functions from the script to be tested
from statvar_imports.commerce_eda import process


class ProcessTest(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.input_csv_path = os.path.join(self.test_dir, "Investment.csv")
        self.output_csv_path = os.path.join(self.test_dir, "Investment1.csv")

        # Mock input CSV content for process_investment_csv
        # This content is designed to test the state/category parsing and numeric cleaning.
        self.mock_input_content = """OriginalHeader1,OriginalHeader2,OriginalHeader3
Alabama,100,200
CategoryA,10,20
California,300,400
CategoryX,50,60
"""
        with open(self.input_csv_path, "w") as f:
            f.write(self.mock_input_content)

        # Expected output CSV content based on current process.py logic
        # Note: The 'Place' in the first data row is due to the 'if index == 0: new_col_a = "Place"' logic
        # and 'header=False' in to_csv.
        self.expected_output_content = """Place,Total,100,200
Alabama,CategoryA,10,20
California,Total,300,400
California,CategoryX,50,60
"""

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_process_investment_csv_success(self):
        # Call the function to be tested
        process.process_investment_csv(self.input_csv_path,
                                       self.output_csv_path, process.us_states)

        # Read the generated output
        with open(self.output_csv_path, "r") as f:
            actual_output_content = f.read()

        # Compare with expected output
        self.assertEqual(actual_output_content.strip(),
                         self.expected_output_content.strip())

    def test_process_investment_csv_empty_input(self):
        empty_input_path = os.path.join(self.test_dir, "empty.csv")
        with open(empty_input_path, "w") as f:
            f.write("")  # Empty file

        # process.py uses absl.logging.fatal which logs CRITICAL and returns normally in unittest context
        # We expect it to log a fatal error for EmptyDataError
        with self.assertLogs(logging.getLogger(), level='FATAL') as cm:
            with self.assertRaises(pd.errors.EmptyDataError):
                process.process_investment_csv(empty_input_path,
                                               self.output_csv_path,
                                               process.us_states)
            self.assertIn("Error: Input file", cm.output[0])
            self.assertIn("is empty", cm.output[0])

    def test_process_investment_csv_file_not_found(self):
        non_existent_path = os.path.join(self.test_dir, "non_existent.csv")

        with self.assertLogs(logging.getLogger(), level='FATAL') as cm:
            with self.assertRaises(FileNotFoundError):
                process.process_investment_csv(non_existent_path,
                                               self.output_csv_path,
                                               process.us_states)
            self.assertIn("Error: Input file not found", cm.output[0])
