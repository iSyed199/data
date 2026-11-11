import unittest
import os
import tempfile
import shutil
import zipfile
import io
from unittest.mock import patch, MagicMock

import requests

# Import the functions to be tested
import download


class DownloadTest(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for output files
        self.test_output_dir = tempfile.mkdtemp()
        # Patch OUTPUT_DIR in download.py to point to our temporary directory
        self.original_output_dir = download.OUTPUT_DIR
        download.OUTPUT_DIR = self.test_output_dir

        # Mock absl flags to prevent UnparsedFlagAccessError
        self.mock_flags_patcher = patch('download._FLAGS')
        self.mock_flags = self.mock_flags_patcher.start()
        self.mock_flags.config_path = 'mock_config.ini'  # Provide a dummy value

        # Mock config file reading
        self.mock_config = MagicMock()
        self.mock_config.__getitem__.return_value = {
            "UN_ZIP_URL": "http://mock.url/data.zip"
        }
        self.mock_config_parser_patcher = patch(
            'download.configparser.ConfigParser', return_value=self.mock_config)
        self.mock_config_parser = self.mock_config_parser_patcher.start()

        # Mock absl.logging.fatal to prevent SystemExit during tests
        self.mock_logging_fatal_patcher = patch('download.logging.fatal')
        self.mock_logging_fatal = self.mock_logging_fatal_patcher.start()
        self.mock_logging_warning_patcher = patch('download.logging.warning')
        self.mock_logging_warning = self.mock_logging_warning_patcher.start()
        self.mock_logging_info_patcher = patch('download.logging.info')
        self.mock_logging_info = self.mock_logging_info_patcher.start()

    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_output_dir)
        # Restore original OUTPUT_DIR
        download.OUTPUT_DIR = self.original_output_dir
        # Stop all patches
        self.mock_config_parser_patcher.stop()
        self.mock_logging_fatal_patcher.stop()
        self.mock_logging_warning_patcher.stop()
        self.mock_logging_info_patcher.stop()
        self.mock_flags_patcher.stop()  # Stop the new patch

    def _create_mock_zip_content(self, csv_filenames, content_map=None):
        """Helper to create mock zip file content."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in csv_filenames:
                file_content = content_map.get(
                    filename, f"header\ndata for {filename}"
                ) if content_map else f"header\ndata for {filename}"
                zf.writestr(filename, file_content)
        return buffer.getvalue()

    @patch('download.requests.get')
    @patch('download.zipfile.is_zipfile')
    def test_successful_download_and_extraction(self, mock_is_zipfile,
                                                mock_requests_get):
        mock_csv_content = "col1,col2\nval1,val2"
        mock_zip_content = self._create_mock_zip_content(
            ['test.csv'], {'test.csv': mock_csv_content})

        mock_response = MagicMock()
        mock_response.content = mock_zip_content
        mock_response.raise_for_status.return_value = None  # Simulate success
        mock_requests_get.return_value = mock_response
        mock_is_zipfile.return_value = True

        zip_path = download.download_file()
        self.assertIsNotNone(zip_path)
        self.assertTrue(os.path.exists(zip_path))
        self.assertEqual(os.path.basename(zip_path), "UNdata_Export.zip")

        download.extract_and_process(zip_path)

        extracted_csv_path = os.path.join(self.test_output_dir, 'test.csv')
        self.assertTrue(os.path.exists(extracted_csv_path))
        with open(extracted_csv_path, 'r') as f:
            self.assertEqual(f.read(), mock_csv_content)
        self.mock_logging_fatal.assert_not_called()

    @patch('download.requests.get')
    def test_download_timeout(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ReadTimeout(
            "Read timed out.")

        zip_path = download.download_file()
        self.assertIsNone(zip_path)  # download_file returns None on fatal error
        self.mock_logging_fatal.assert_called_once()
        self.assertIn("Failed to download file",
                      self.mock_logging_fatal.call_args[0][0])

    @patch('download.requests.get')
    @patch('download.zipfile.is_zipfile')
    def test_invalid_zip_file_from_server(self, mock_is_zipfile,
                                          mock_requests_get):
        mock_response = MagicMock()
        mock_response.content = b"this is not a zip file"
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        mock_is_zipfile.return_value = False  # Explicitly say it's not a zip

        zip_path = download.download_file()
        self.assertIsNone(zip_path)
        self.mock_logging_fatal.assert_called_once()
        self.assertIn("Failed to obtain a valid ZIP file",
                      self.mock_logging_fatal.call_args[0][0])
        self.assertEqual(self.mock_logging_warning.call_count,
                         4)  # Warning about invalid zip content

    @patch('download.requests.get')
    @patch('download.zipfile.is_zipfile')
    def test_zip_file_no_csvs(self, mock_is_zipfile, mock_requests_get):
        mock_zip_content = self._create_mock_zip_content(['not_a_csv.txt'])

        mock_response = MagicMock()
        mock_response.content = mock_zip_content
        mock_response.raise_for_status.return_value = None
        mock_requests_get.return_value = mock_response
        mock_is_zipfile.return_value = True

        zip_path = download.download_file()
        self.assertIsNotNone(zip_path)  # Download itself is successful

        download.extract_and_process(zip_path)
        self.mock_logging_fatal.assert_called_once()
        self.assertIn("No CSV files found",
                      self.mock_logging_fatal.call_args[0][0])

    @patch('download.requests.get')
    @patch('download.zipfile.is_zipfile')
    def test_http_error(self, mock_is_zipfile, mock_requests_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found")
        mock_requests_get.return_value = mock_response
        mock_is_zipfile.return_value = True  # Doesn't matter if HTTP error occurs before content check

        zip_path = download.download_file()
        self.assertIsNone(zip_path)
        self.mock_logging_fatal.assert_called_once()
        self.assertIn("Failed to download file",
                      self.mock_logging_fatal.call_args[0][0])
