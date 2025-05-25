import unittest
from unittest.mock import patch, MagicMock
import geopandas as gpd
import pandas as pd # Required for MagicMock spec for GeoDataFrame

# Adjust import path if necessary, depending on how tests are run
from skyline_agent.gis_utils import load_buildings, load_roads, load_land_use

class TestGisUtils(unittest.TestCase):

    @patch('skyline_agent.gis_utils.gpd.read_file')
    def test_load_buildings_success(self, mock_read_file):
        """Test load_buildings successfully loads a file."""
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read_file.return_value = mock_gdf
        
        file_path = "dummy_buildings.shp"
        result = load_buildings(file_path)
        
        mock_read_file.assert_called_once_with(file_path)
        self.assertEqual(result, mock_gdf)

    @patch('skyline_agent.gis_utils.gpd.read_file')
    @patch('builtins.print')
    def test_load_buildings_file_not_found(self, mock_print, mock_read_file):
        """Test load_buildings handles FileNotFoundError."""
        mock_read_file.side_effect = FileNotFoundError("File not found")
        
        file_path = "non_existent_buildings.shp"
        result = load_buildings(file_path)
        
        mock_read_file.assert_called_once_with(file_path)
        mock_print.assert_called_once_with(f"Error: File not found at {file_path}")
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertTrue(result.empty)

    @patch('skyline_agent.gis_utils.gpd.read_file')
    def test_load_roads_success(self, mock_read_file):
        """Test load_roads successfully loads a file."""
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read_file.return_value = mock_gdf
        
        file_path = "dummy_roads.shp"
        result = load_roads(file_path)
        
        mock_read_file.assert_called_once_with(file_path)
        self.assertEqual(result, mock_gdf)

    @patch('skyline_agent.gis_utils.gpd.read_file')
    @patch('builtins.print')
    def test_load_roads_file_not_found(self, mock_print, mock_read_file):
        """Test load_roads handles FileNotFoundError."""
        mock_read_file.side_effect = FileNotFoundError("File not found")
        
        file_path = "non_existent_roads.shp"
        result = load_roads(file_path)
        
        mock_read_file.assert_called_once_with(file_path)
        mock_print.assert_called_once_with(f"Error: File not found at {file_path}")
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertTrue(result.empty)

    @patch('skyline_agent.gis_utils.gpd.read_file')
    def test_load_land_use_success(self, mock_read_file):
        """Test load_land_use successfully loads a file."""
        mock_gdf = MagicMock(spec=gpd.GeoDataFrame)
        mock_read_file.return_value = mock_gdf
        
        file_path = "dummy_land_use.shp"
        result = load_land_use(file_path)
        
        mock_read_file.assert_called_once_with(file_path)
        self.assertEqual(result, mock_gdf)

    @patch('skyline_agent.gis_utils.gpd.read_file')
    @patch('builtins.print')
    def test_load_land_use_file_not_found(self, mock_print, mock_read_file):
        """Test load_land_use handles FileNotFoundError."""
        mock_read_file.side_effect = FileNotFoundError("File not found")
        
        file_path = "non_existent_land_use.shp"
        result = load_land_use(file_path)
        
        mock_read_file.assert_called_once_with(file_path)
        mock_print.assert_called_once_with(f"Error: File not found at {file_path}")
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertTrue(result.empty)

    @patch('skyline_agent.gis_utils.gpd.read_file')
    @patch('builtins.print')
    def test_load_buildings_generic_exception(self, mock_print, mock_read_file):
        """Test load_buildings handles a generic exception."""
        mock_read_file.side_effect = Exception("Some generic error")
        
        file_path = "problematic_buildings.shp"
        result = load_buildings(file_path)
        
        mock_read_file.assert_called_once_with(file_path)
        mock_print.assert_called_once_with(f"Error loading building data from {file_path}: Some generic error")
        self.assertIsInstance(result, gpd.GeoDataFrame)
        self.assertTrue(result.empty)

if __name__ == '__main__':
    unittest.main()
