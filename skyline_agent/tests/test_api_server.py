import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import geopandas as gpd
from shapely.geometry import Polygon

# Import the FastAPI app instance from your server code
# Adjust the import path if your file structure is different or if you have a factory function for app creation
# Assuming api_server.py is in skyline_agent directory and tests are run from project root
from skyline_agent.api_server import app 

class TestApiServer(unittest.TestCase):
    def setUp(self):
        """Set up the test client before each test."""
        self.client = TestClient(app)
        
        # Create a minimal mock GeoDataFrame for successful loads
        self.mock_gdf = gpd.GeoDataFrame({'id': [1], 'geometry': [Polygon([(0,0), (1,0), (1,1), (0,1)])]})
        self.mock_land_use_gdf = gpd.GeoDataFrame({'plot_ID': ['P1'], 'geometry': [Polygon([(0,0), (10,0), (10,10), (0,10)])]})
        self.mock_target_plot_geom = Polygon([(0,0), (10,0), (10,10), (0,10)])


    @patch('skyline_agent.api_server.shutil.rmtree') # Mock shutil.rmtree first
    @patch('skyline_agent.api_server.os.makedirs')
    @patch('skyline_agent.api_server.os.path.exists')
    @patch('skyline_agent.api_server.generate_building_tileset')
    @patch('skyline_agent.api_server.recommend_building_height')
    @patch('skyline_agent.api_server.get_target_plot')
    @patch('skyline_agent.api_server.load_land_use')
    @patch('skyline_agent.api_server.load_buildings')
    def test_get_scene_data_success(self, mock_load_buildings, mock_load_land_use, 
                                    mock_get_target_plot, mock_recommend_height, 
                                    mock_generate_tileset, mock_os_path_exists, 
                                    mock_os_makedirs, mock_shutil_rmtree):
        """Test the /scene_data endpoint for a successful case."""
        # Configure mock return values
        mock_load_buildings.return_value = self.mock_gdf
        mock_load_land_use.return_value = self.mock_land_use_gdf
        mock_get_target_plot.return_value = self.mock_target_plot_geom
        mock_recommend_height.return_value = 50.0
        mock_generate_tileset.return_value = True
        mock_os_path_exists.return_value = False # Assume tileset dir doesn't exist initially or for specific sub-path

        # Make a GET request to the endpoint
        response = self.client.get("/scene_data/?buildings_file=fake/buildings.shp&land_use_file=fake/land_use.shp&target_plot_id=P1&height_column=h")

        # Assertions
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        
        self.assertIn("tileset_url", json_response)
        self.assertTrue(json_response["tileset_url"].endswith("/tileset.json"))
        
        self.assertIn("height_recommendation", json_response)
        self.assertIsNotNone(json_response["height_recommendation"])
        self.assertEqual(json_response["height_recommendation"]["value"], 50.0)
        self.assertEqual(json_response["height_recommendation"]["plot_id"], "P1")
        self.assertIsInstance(json_response["height_recommendation"]["position"], list)
        self.assertEqual(len(json_response["height_recommendation"]["position"]), 3)

        # Assert that mocked functions were called
        mock_load_buildings.assert_called_once()
        mock_load_land_use.assert_called_once()
        mock_get_target_plot.assert_called_once()
        mock_recommend_height.assert_called_once()
        mock_generate_tileset.assert_called_once()
        # mock_os_path_exists.assert_called() # Called multiple times potentially
        # mock_os_makedirs.assert_called() # Called multiple times potentially


    @patch('skyline_agent.api_server.load_buildings')
    def test_get_scene_data_building_data_not_found(self, mock_load_buildings):
        """Test /scene_data when building data is not found."""
        mock_load_buildings.return_value = None # Simulate file not found or empty GDF

        response = self.client.get("/scene_data/?buildings_file=nonexistent.shp")
        
        self.assertEqual(response.status_code, 404)
        json_response = response.json()
        self.assertIn("detail", json_response)
        # The actual path in the detail message will be absolute due to os.getcwd()
        # So, we check if the provided relative path is part of the message.
        self.assertTrue("nonexistent.shp" in json_response["detail"])


    @patch('skyline_agent.api_server.load_land_use')
    @patch('skyline_agent.api_server.load_buildings')
    def test_get_scene_data_land_use_data_not_found(self, mock_load_buildings, mock_load_land_use):
        """Test /scene_data when land use data is not found."""
        mock_load_buildings.return_value = self.mock_gdf # Buildings load successfully
        mock_load_land_use.return_value = None # Land use data not found

        response = self.client.get("/scene_data/?land_use_file=nonexistent_lu.shp")
        
        self.assertEqual(response.status_code, 404)
        json_response = response.json()
        self.assertIn("detail", json_response)
        self.assertTrue("nonexistent_lu.shp" in json_response["detail"])


    @patch('skyline_agent.api_server.shutil.rmtree')
    @patch('skyline_agent.api_server.os.makedirs')
    @patch('skyline_agent.api_server.os.path.exists')
    @patch('skyline_agent.api_server.generate_building_tileset')
    @patch('skyline_agent.api_server.recommend_building_height')
    @patch('skyline_agent.api_server.get_target_plot')
    @patch('skyline_agent.api_server.load_land_use')
    @patch('skyline_agent.api_server.load_buildings')
    def test_get_scene_data_tileset_generation_fails(self, mock_load_buildings, mock_load_land_use,
                                                    mock_get_target_plot, mock_recommend_height,
                                                    mock_generate_tileset, mock_os_path_exists,
                                                    mock_os_makedirs, mock_shutil_rmtree):
        """Test /scene_data when tileset generation fails."""
        mock_load_buildings.return_value = self.mock_gdf
        mock_load_land_use.return_value = self.mock_land_use_gdf
        mock_get_target_plot.return_value = self.mock_target_plot_geom
        mock_recommend_height.return_value = 50.0
        mock_generate_tileset.return_value = False # Simulate failure
        mock_os_path_exists.return_value = False

        response = self.client.get("/scene_data/")
        
        self.assertEqual(response.status_code, 500)
        json_response = response.json()
        self.assertIn("detail", json_response)
        self.assertEqual(json_response["detail"], "Failed to generate 3D tileset.")


    @patch('skyline_agent.api_server.shutil.rmtree')
    @patch('skyline_agent.api_server.os.makedirs')
    @patch('skyline_agent.api_server.os.path.exists')
    @patch('skyline_agent.api_server.generate_building_tileset')
    @patch('skyline_agent.api_server.recommend_building_height') # Still need this for the call chain
    @patch('skyline_agent.api_server.get_target_plot')
    @patch('skyline_agent.api_server.load_land_use')
    @patch('skyline_agent.api_server.load_buildings')
    def test_get_scene_data_target_plot_not_found(self, mock_load_buildings, mock_load_land_use,
                                                 mock_get_target_plot, mock_recommend_height, 
                                                 mock_generate_tileset, mock_os_path_exists,
                                                 mock_os_makedirs, mock_shutil_rmtree):
        """Test /scene_data when the target plot is not found."""
        mock_load_buildings.return_value = self.mock_gdf
        mock_load_land_use.return_value = self.mock_land_use_gdf
        mock_get_target_plot.return_value = None # Target plot not found
        mock_generate_tileset.return_value = True # Tileset generation is successful
        mock_os_path_exists.return_value = False
        # recommend_building_height should not be called if plot is None, so no need to mock its return value specifically for this path.

        response = self.client.get("/scene_data/?target_plot_id=NonExistentP")
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertIn("tileset_url", json_response) # Tileset should still be generated
        self.assertIsNone(json_response["height_recommendation"]) # No recommendation if plot not found


    @patch('skyline_agent.api_server.shutil.rmtree')
    @patch('skyline_agent.api_server.os.makedirs')
    @patch('skyline_agent.api_server.os.path.exists')
    @patch('skyline_agent.api_server.generate_building_tileset')
    @patch('skyline_agent.api_server.recommend_building_height')
    @patch('skyline_agent.api_server.get_target_plot')
    @patch('skyline_agent.api_server.load_land_use')
    @patch('skyline_agent.api_server.load_buildings')
    def test_get_scene_data_height_recommendation_not_possible(self, mock_load_buildings, mock_load_land_use,
                                                            mock_get_target_plot, mock_recommend_height,
                                                            mock_generate_tileset, mock_os_path_exists,
                                                            mock_os_makedirs, mock_shutil_rmtree):
        """Test /scene_data when height recommendation is not possible (returns None)."""
        mock_load_buildings.return_value = self.mock_gdf
        mock_load_land_use.return_value = self.mock_land_use_gdf
        mock_get_target_plot.return_value = self.mock_target_plot_geom # Plot is found
        mock_recommend_height.return_value = None # But recommendation is not possible
        mock_generate_tileset.return_value = True
        mock_os_path_exists.return_value = False

        response = self.client.get("/scene_data/")
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertIn("tileset_url", json_response)
        self.assertIsNone(json_response["height_recommendation"])

if __name__ == '__main__':
    unittest.main()
