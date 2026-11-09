import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock, call

# Add the directory containing download.py to the path
# Assuming download_test.py is in the same directory as download.py
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the functions to be tested
# We need to import the module itself to patch its functions
import download as download_script


class DownloadScriptTest(unittest.TestCase):

    def setUp(self):
        # Create temporary directories for testing
        self.temp_base_download_dir = tempfile.mkdtemp()
        self.temp_source_files_dir = tempfile.mkdtemp()

        # Patch the global variables in download.py to use our temporary directories
        self.patch_base_download_dir = patch.object(download_script,
                                                    '_BASE_DOWNLOAD_DIRECTORY',
                                                    self.temp_base_download_dir)
        self.patch_source_files_dir = patch.object(download_script,
                                                   '_SOURCE_FILES_DIRECTORY',
                                                   self.temp_source_files_dir)

        self.patch_base_download_dir.start()
        self.patch_source_files_dir.start()

        # Mock pandas DataFrame and its to_csv method
        self.mock_df = MagicMock()
        self.mock_df.to_csv = MagicMock()

        # Mock pandas read_csv and read_excel
        self.patch_read_csv = patch('pandas.read_csv',
                                    return_value=self.mock_df)
        self.patch_read_excel = patch('pandas.read_excel',
                                      return_value=self.mock_df)

        self.mock_read_csv = self.patch_read_csv.start()
        self.mock_read_excel = self.patch_read_excel.start()

        # Mock glob.glob
        self.patch_glob = patch('glob.glob')
        self.mock_glob = self.patch_glob.start()

        # Mock os.path.isdir
        self.patch_isdir = patch('os.path.isdir', return_value=True)
        self.mock_isdir = self.patch_isdir.start()

        # Mock logging to suppress output during tests
        self.patch_logging_info = patch('absl.logging.info')
        self.mock_logging_info = self.patch_logging_info.start()
        self.patch_logging_fatal = patch('absl.logging.fatal')
        self.mock_logging_fatal = self.patch_logging_fatal.start()

    def tearDown(self):
        # Clean up temporary directories
        shutil.rmtree(self.temp_base_download_dir)
        shutil.rmtree(self.temp_source_files_dir)

        # Stop all patches
        self.patch_base_download_dir.stop()
        self.patch_source_files_dir.stop()
        self.patch_read_csv.stop()
        self.patch_read_excel.stop()
        self.patch_glob.stop()
        self.patch_isdir.stop()
        self.patch_logging_info.stop()
        self.patch_logging_fatal.stop()

    def test_find_and_collect_files_single_csv(self):
        """
        Tests _find_and_collect_files when a single CSV file is found.
        Should result in a filename without _part_XX.
        """
        year_range = "2011-12"
        # Simulate glob.glob finding one CSV file
        self.mock_glob.side_effect = [
            [  # 1. For potential_dirs
                os.path.join(self.temp_base_download_dir, 'crdc_data_2011-12',
                             'Harassment')
            ],
            [  # 2. For *.csv
                os.path.join(self.temp_base_download_dir, 'crdc_data_2011-12',
                             'Harassment', 'data.csv')
            ],
            []  # 3. For *.xlsx (no xlsx files in this test case)
        ]

        download_script._find_and_collect_files(year_range)

        # Assert that pandas.read_csv was called
        self.mock_read_csv.assert_called_once_with(
            os.path.join(self.temp_base_download_dir, 'crdc_data_2011-12',
                         'Harassment', 'data.csv'))

        # Assert that to_csv was called with the correct filename (2012 is the second year of 2011-12)
        expected_output_path = os.path.join(
            self.temp_source_files_dir, 'crdc_harassment_or_bullying_2012.csv')
        self.mock_df.to_csv.assert_called_once_with(expected_output_path,
                                                    index=False)
        self.mock_read_excel.assert_not_called()

    def test_find_and_collect_files_multiple_csvs(self):
        """
        Tests _find_and_collect_files when multiple CSV files are found.
        Should result in filenames with _part_01, _part_02.
        """
        year_range = "2013-14"
        # Simulate glob.glob finding two CSV files
        file1 = os.path.join(self.temp_base_download_dir, 'crdc_data_2013-14',
                             'Harassment', 'data_part1.csv')
        file2 = os.path.join(self.temp_base_download_dir, 'crdc_data_2013-14',
                             'Harassment', 'data_part2.csv')
        self.mock_glob.side_effect = [
            [file1, file2],  # For file_paths.extend
            []  # For potential_dirs (since 2013-14 is not 2009-10 or 2011-12)
        ]

        download_script._find_and_collect_files(year_range)

        # Assert that pandas.read_csv was called for both files
        self.mock_read_csv.assert_has_calls(
            [call(file1), call(file2)], any_order=True)

        # Assert that to_csv was called with correct part numbering (2014 is the second year of 2013-14)
        expected_output_path_1 = os.path.join(
            self.temp_source_files_dir,
            'crdc_harassment_or_bullying_2014_part_01.csv')
        expected_output_path_2 = os.path.join(
            self.temp_source_files_dir,
            'crdc_harassment_or_bullying_2014_part_02.csv')
        self.mock_df.to_csv.assert_has_calls([
            call(expected_output_path_1, index=False),
            call(expected_output_path_2, index=False)
        ],
                                             any_order=True)
        self.assertEqual(self.mock_df.to_csv.call_count, 2)
        self.mock_read_excel.assert_not_called()

    def test_find_and_collect_files_mix_csv_xlsx(self):
        """
        Tests _find_and_collect_files when a mix of CSV and XLSX files are found.
        All should be converted to CSV.
        """
        year_range = "2015-16"
        # Simulate glob.glob finding one CSV and one XLSX file
        csv_file = os.path.join(self.temp_base_download_dir,
                                'crdc_data_2015-16', 'Harassment', 'data.csv')
        xlsx_file = os.path.join(self.temp_base_download_dir,
                                 'crdc_data_2015-16', 'Harassment', 'data.xlsx')
        self.mock_glob.side_effect = [
            [csv_file, xlsx_file],  # For file_paths.extend
            []  # For potential_dirs
        ]

        download_script._find_and_collect_files(year_range)

        # Assert that pandas.read_csv was called for the CSV and read_excel for XLSX
        self.mock_read_csv.assert_called_once_with(csv_file)
        self.mock_read_excel.assert_called_once_with(xlsx_file, sheet_name=0)

        # Assert that to_csv was called for both, with correct part numbering
        expected_output_path_1 = os.path.join(
            self.temp_source_files_dir,
            'crdc_harassment_or_bullying_2016_part_01.csv')
        expected_output_path_2 = os.path.join(
            self.temp_source_files_dir,
            'crdc_harassment_or_bullying_2016_part_02.csv')
        self.mock_df.to_csv.assert_has_calls([
            call(expected_output_path_1, index=False),
            call(expected_output_path_2, index=False)
        ],
                                             any_order=True)
        self.assertEqual(self.mock_df.to_csv.call_count, 2)

    def test_find_and_collect_files_no_files_found(self):
        """
        Tests _find_and_collect_files when no files are found.
        Should not call read_csv, read_excel, or to_csv.
        """
        year_range = "2019-20"
        self.mock_glob.side_effect = [
            [],  # For file_paths.extend
            []  # For potential_dirs
        ]

        download_script._find_and_collect_files(year_range)

        self.mock_read_csv.assert_not_called()
        self.mock_read_excel.assert_not_called()
        self.mock_df.to_csv.assert_not_called()
        self.mock_logging_info.assert_any_call(
            "No Harassment data files found for 2019-20.")

    def test_find_and_collect_files_unsupported_format(self):
        """
        Tests _find_and_collect_files with an unsupported file format.
        Should skip the unsupported file.
        """
        year_range = "2017-18"
        unsupported_file = os.path.join(self.temp_base_download_dir,
                                        'crdc_data_2017-18', 'Harassment',
                                        'data.txt')
        csv_file = os.path.join(self.temp_base_download_dir,
                                'crdc_data_2017-18', 'Harassment', 'data.csv')
        self.mock_glob.side_effect = [
            [unsupported_file, csv_file],  # For file_paths.extend
            []  # For potential_dirs
        ]

        download_script._find_and_collect_files(year_range)

        # Only the CSV file should be processed
        self.mock_read_csv.assert_called_once_with(csv_file)
        self.mock_read_excel.assert_not_called()

        expected_output_path = os.path.join(
            self.temp_source_files_dir,
            'crdc_harassment_or_bullying_2018_part_01.csv')
        self.mock_df.to_csv.assert_called_once_with(expected_output_path,
                                                    index=False)
        self.mock_logging_info.assert_any_call(
            f"Skipping {unsupported_file}: Unsupported original format .txt.")

    def test_find_and_collect_files_target_dir_pattern_2011_12(self):
        """
        Tests the specific targeted folder search for 2011-12.
        """
        year_range = "2011-12"
        harassment_dir = os.path.join(self.temp_base_download_dir,
                                      'crdc_data_2011-12', 'SubDir',
                                      'Harassment Data')
        csv_file = os.path.join(harassment_dir, 'actual_data.csv')

        # Mock glob.glob to return the specific harassment directory first, then the files inside it
        self.mock_glob.side_effect = [
            [harassment_dir],  # For potential_dirs
            [csv_file],  # For files inside the target_dir
            []  # For xlsx files
        ]

        download_script._find_and_collect_files(year_range)

        # Assert that the correct directory was found and its files processed
        self.mock_logging_info.assert_any_call(
            f"Found Harassment folder for {year_range}: {harassment_dir}")
        self.mock_read_csv.assert_called_once_with(csv_file)
        expected_output_path = os.path.join(
            self.temp_source_files_dir, 'crdc_harassment_or_bullying_2012.csv')
        self.mock_df.to_csv.assert_called_once_with(expected_output_path,
                                                    index=False)


if __name__ == '__main__':
    unittest.main()
