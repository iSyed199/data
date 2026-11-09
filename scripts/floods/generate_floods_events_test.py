import unittest
from unittest import mock
import os
import sys

# Save original sys.argv and clear it to prevent absl.flags from parsing test runner arguments
_original_argv = list(sys.argv)
sys.argv = [sys.argv[0]]

# Add parent directories to path for imports
_SCRIPTS_DIR = os.path.dirname(__file__)
sys.path.append(_SCRIPTS_DIR)
sys.path.append(os.path.dirname(_SCRIPTS_DIR))
sys.path.append(os.path.dirname(os.path.dirname(_SCRIPTS_DIR)))
sys.path.append(os.path.join(os.path.dirname(_SCRIPTS_DIR), 'earthengine'))
sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(_SCRIPTS_DIR)), 'util'))

# Import the script to be tested
import generate_floods_events

# Restore original sys.argv after imports
sys.argv = _original_argv


class GenerateFloodsEventsTest(unittest.TestCase):

    @mock.patch('generate_floods_events.EventPipeline')
    @mock.patch('generate_floods_events.ConfigMap')
    @mock.patch('generate_floods_events._FLAGS')  # Mock absl flags
    def test_main_function_calls_pipeline(self, mock_flags, MockConfigMap,
                                          MockEventPipeline):
        # Set up mock flags
        mock_flags.flood_pipeline_config = os.path.join(
            _SCRIPTS_DIR, 'flood_events_pipeline_config.py')
        mock_flags.start_date = ''
        mock_flags.flood_pipeline_stages = []

        # Mock ConfigMap instance and its get method
        mock_config_instance = mock.Mock()
        MockConfigMap.return_value = mock_config_instance
        mock_config_instance.get.return_value = {
        }  # Return empty dict for defaults

        # Mock EventPipeline instance and its run method
        mock_pipeline_instance = mock.Mock()
        MockEventPipeline.return_value = mock_pipeline_instance

        # Call the main function
        generate_floods_events.main([])

        # Assertions
        MockConfigMap.assert_called_once_with(
            filename=mock_flags.flood_pipeline_config)
        MockEventPipeline.assert_called_once_with(config=mock_config_instance)
        mock_pipeline_instance.run.assert_called_once_with(run_stages=[])

    @mock.patch('generate_floods_events.EventPipeline')
    @mock.patch('generate_floods_events.ConfigMap')
    @mock.patch('generate_floods_events._FLAGS')
    def test_main_function_with_start_date_and_stages(self, mock_flags,
                                                      MockConfigMap,
                                                      MockEventPipeline):
        # Set up mock flags with specific values
        mock_flags.flood_pipeline_config = os.path.join(
            _SCRIPTS_DIR, 'flood_events_pipeline_config.py')
        mock_flags.start_date = '2023-01-01'
        mock_flags.flood_pipeline_stages = ['earthengine', 'raster_csv']

        mock_config_instance = mock.Mock()
        MockConfigMap.return_value = mock_config_instance
        mock_config_instance.get.return_value = {}  # Ensure get is called

        mock_pipeline_instance = mock.Mock()
        MockEventPipeline.return_value = mock_pipeline_instance

        generate_floods_events.main([])

        # Assertions
        MockConfigMap.assert_called_once_with(
            filename=mock_flags.flood_pipeline_config)
        # Check that start_date was set in the config
        mock_config_instance.get.assert_called_with('defaults', {})
        self.assertEqual(
            mock_config_instance.get('defaults', {})['start_date'],
            '2023-01-01')
        MockEventPipeline.assert_called_once_with(config=mock_config_instance)
        mock_pipeline_instance.run.assert_called_once_with(
            run_stages=['earthengine', 'raster_csv'])


if __name__ == '__main__':
    unittest.main()
