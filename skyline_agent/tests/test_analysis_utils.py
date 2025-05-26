import unittest
from unittest.mock import patch
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, Point

from skyline_agent.analysis_utils import get_target_plot, recommend_building_height

class TestAnalysisUtils(unittest.TestCase):

    def setUp(self):
        """Set up test data for the test methods."""
        # Sample Land Use Data
        land_use_data = {
            'plot_ID': ['P1', 'P2', 'P3'],
            'geometry': [
                Polygon([(0, 0), (0, 10), (10, 10), (10, 0)]),
                Polygon([(10, 0), (10, 10), (20, 10), (20, 0)]),
                Polygon([(20, 0), (20, 10), (30, 10), (30, 0)])
            ]
        }
        self.land_use_gdf = gpd.GeoDataFrame(land_use_data, crs="EPSG:32632")

        # Sample Buildings Data
        buildings_data = {
            'building_ID': ['B1', 'B2', 'B3', 'B4', 'B5', 'B6'],
            'height': [10, 15, 'twenty', None, 20, 30], # Includes invalid and missing height
            'geometry': [
                Polygon([(1, 1), (1, 2), (2, 2), (2, 1)]),      # Near P1
                Polygon([(3, 3), (3, 4), (4, 4), (4, 3)]),      # Near P1
                Polygon([(11, 1), (11, 2), (12, 2), (12, 1)]),   # Near P2 (invalid height)
                Polygon([(13, 3), (13, 4), (14, 4), (14, 3)]),   # Near P2 (None height)
                Polygon([(50, 50), (50, 51), (51, 51), (51, 50)]), # Far from P1, P2
                Polygon([(8, 8), (8, 9), (9, 9), (9, 8)])       # Near P1, height 30
            ]
        }
        self.buildings_gdf = gpd.GeoDataFrame(buildings_data, crs="EPSG:32632")
        
        self.empty_gdf = gpd.GeoDataFrame({'geometry': []}, crs="EPSG:32632")


    # --- Tests for get_target_plot ---
    def test_get_target_plot_success(self):
        """Test finding an existing plot by ID."""
        target_geom = get_target_plot(self.land_use_gdf, 'plot_ID', 'P2')
        self.assertIsNotNone(target_geom)
        self.assertTrue(target_geom.equals(self.land_use_gdf.geometry.iloc[1]))

    def test_get_target_plot_non_existent_id(self):
        """Test with a non-existent plot ID."""
        target_geom = get_target_plot(self.land_use_gdf, 'plot_ID', 'P99')
        self.assertIsNone(target_geom)

    def test_get_target_plot_empty_gdf(self):
        """Test with an empty land use GeoDataFrame."""
        target_geom = get_target_plot(self.empty_gdf, 'plot_ID', 'P1')
        self.assertIsNone(target_geom)
        
    @patch('builtins.print') # Suppress print warnings for this test
    def test_get_target_plot_missing_column(self, mock_print):
        """Test with a missing plot_ID_column in the GeoDataFrame."""
        target_geom = get_target_plot(self.land_use_gdf, 'non_existent_column', 'P1')
        self.assertIsNone(target_geom)
        mock_print.assert_called_with("Warning: Column 'non_existent_column' not found in the land_use GeoDataFrame.")

    # --- Tests for recommend_building_height ---
    def test_recommend_height_success(self):
        """Test height recommendation with valid surrounding buildings."""
        target_plot_geometry = self.land_use_gdf.geometry.iloc[0] # Geometry of P1
        # Expected nearby buildings for P1 (buffer 50): B1 (10m), B2 (15m), B6 (30m)
        # Average = (10 + 15 + 30) / 3 = 55 / 3 = 18.333...
        recommended = recommend_building_height(target_plot_geometry, self.buildings_gdf, 'height', buffer_distance=5) 
        self.assertAlmostEqual(recommended, (10 + 15 + 30) / 3, places=2)

    def test_recommend_height_no_buildings_in_buffer(self):
        """Test with no buildings within the buffer distance."""
        target_plot_geometry = self.land_use_gdf.geometry.iloc[0] # P1
        # Using a very small buffer that won't include any buildings
        recommended = recommend_building_height(target_plot_geometry, self.buildings_gdf, 'height', buffer_distance=0.1)
        self.assertIsNone(recommended)

    def test_recommend_height_invalid_height_data(self):
        """Test with buildings having invalid or missing height data."""
        target_plot_geometry = self.land_use_gdf.geometry.iloc[1] # P2
        # Nearby buildings for P2: B3 ('twenty'), B4 (None). No valid heights.
        # This will use a default buffer_distance of 50.
        # Buildings near P2 (within 50m): B1, B2, B3, B4, B6
        # B1 (10), B2 (15), B3(invalid), B4(None), B6(30)
        # Valid heights: 10, 15, 30. Average = (10+15+30)/3 = 18.333
        recommended = recommend_building_height(target_plot_geometry, self.buildings_gdf, 'height', buffer_distance=10)
        self.assertAlmostEqual(recommended, (10 + 15 + 30) / 3, places=2) # B1, B2, B6 should be within 10m of P2 (center 15,0)

    @patch('builtins.print') # Suppress print warnings
    def test_recommend_height_target_plot_none(self, mock_print):
        """Test when target_plot_geometry is None."""
        recommended = recommend_building_height(None, self.buildings_gdf, 'height')
        self.assertIsNone(recommended)
        mock_print.assert_any_call("Warning: Target plot geometry is None. Cannot recommend height.")

    def test_recommend_height_empty_buildings_gdf(self):
        """Test with an empty surrounding_buildings_gdf."""
        target_plot_geometry = self.land_use_gdf.geometry.iloc[0]
        recommended = recommend_building_height(target_plot_geometry, self.empty_gdf, 'height')
        self.assertIsNone(recommended)

    @patch('builtins.print') # Suppress print warnings
    def test_recommend_height_missing_height_column(self, mock_print):
        """Test when the height_column is not in buildings_gdf."""
        target_plot_geometry = self.land_use_gdf.geometry.iloc[0]
        recommended = recommend_building_height(target_plot_geometry, self.buildings_gdf, 'non_existent_height_col')
        self.assertIsNone(recommended)
        mock_print.assert_any_call("Warning: Height column 'non_existent_height_col' not found in surrounding buildings GeoDataFrame.")
        
    def test_recommend_height_only_invalid_heights_nearby(self):
        """Test when only buildings with invalid heights are nearby."""
        # Create a specific building GDF for this test
        invalid_buildings_data = {
            'height': ['error', None, 'thirty'],
            'geometry': [
                Polygon([(1, 1), (1, 2), (2, 2), (2, 1)]), # Near P1
                Polygon([(3, 3), (3, 4), (4, 4), (4, 3)]), # Near P1
                Polygon([(8, 8), (8, 9), (9, 9), (9, 8)])  # Near P1
            ]
        }
        invalid_buildings_gdf = gpd.GeoDataFrame(invalid_buildings_data, crs="EPSG:32632")
        target_plot_geometry = self.land_use_gdf.geometry.iloc[0] # P1
        recommended = recommend_building_height(target_plot_geometry, invalid_buildings_gdf, 'height', buffer_distance=5)
        self.assertIsNone(recommended)

    def test_recommend_height_geoseries_input(self):
        """Test recommend_building_height when target_plot_geometry is a GeoSeries."""
        target_plot_geoseries = self.land_use_gdf[self.land_use_gdf['plot_ID'] == 'P1'].geometry
        self.assertIsInstance(target_plot_geoseries, gpd.GeoSeries)
        recommended = recommend_building_height(target_plot_geoseries, self.buildings_gdf, 'height', buffer_distance=5)
        self.assertAlmostEqual(recommended, (10 + 15 + 30) / 3, places=2)

    @patch('builtins.print')
    def test_recommend_height_empty_geoseries_input(self, mock_print):
        """Test recommend_building_height with an empty GeoSeries."""
        empty_geoseries = self.land_use_gdf[self.land_use_gdf['plot_ID'] == 'P99'].geometry # Non-existent ID
        self.assertTrue(empty_geoseries.empty)
        recommended = recommend_building_height(empty_geoseries, self.buildings_gdf, 'height')
        self.assertIsNone(recommended)
        mock_print.assert_any_call("Warning: Target plot GeoSeries is empty. Cannot recommend height.")


if __name__ == '__main__':
    unittest.main()
