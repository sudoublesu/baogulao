import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import shutil
import json
import geopandas as gpd
from shapely.geometry import Polygon
import trimesh # For comparison or deep inspection if needed

# Adjust import path based on test execution context
from skyline_agent.threed_tiles_utils import create_glb_from_building, generate_building_tileset

class TestThreeDTilesUtils(unittest.TestCase):

    def setUp(self):
        """Set up test data and directories."""
        self.sample_polygon = Polygon([(0, 0), (0, 10), (10, 10), (10, 0)])
        self.sample_height = 20.0
        self.sample_attributes = {"id": "B1", "name": "Test Building"}
        
        self.test_output_dir = "test_generated_tileset"
        # Ensure cleanup happens even if setUp fails partially
        self.addCleanup(self._cleanup_test_output_dir)


    def _cleanup_test_output_dir(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    # --- Tests for create_glb_from_building ---
    def test_create_glb_from_building_success(self):
        """Test successful GLB creation from a valid building polygon and height."""
        glb_bytes = create_glb_from_building(self.sample_polygon, self.sample_height, self.sample_attributes)
        self.assertIsNotNone(glb_bytes)
        self.assertIsInstance(glb_bytes, bytes)
        self.assertTrue(len(glb_bytes) > 0)
        
        # Optional: Deeper inspection by trying to load it with trimesh
        try:
            mesh = trimesh.load_mesh(io.BytesIO(glb_bytes), file_type='glb')
            self.assertIsNotNone(mesh)
            self.assertTrue(len(mesh.vertices) > 0)
            self.assertTrue(len(mesh.faces) > 0)
            if "name" in self.sample_attributes: # Check if metadata was somewhat passed
                 # Trimesh metadata handling can be complex (scene vs geometry).
                 # This check is very basic.
                 # For trimesh, metadata often lands in scene.graph[scene.graph.transforms.tolist().index(trimesh.transformations.identity_matrix())]['extras']
                 # or mesh.metadata (if set directly as in the function)
                 self.assertEqual(mesh.metadata.get("name"), self.sample_attributes["name"])
        except Exception as e:
            self.fail(f"Failed to load generated GLB with trimesh: {e}")


    def test_create_glb_invalid_polygon(self):
        """Test GLB creation with an invalid polygon (e.g., too few points)."""
        invalid_poly = Polygon([(0,0), (1,1)]) # Line, not a polygon for extrusion
        glb_bytes = create_glb_from_building(invalid_poly, self.sample_height)
        self.assertIsNone(glb_bytes) # Expect None due to internal checks

    def test_create_glb_non_positive_height(self):
        """Test GLB creation with non-positive height."""
        glb_bytes_zero = create_glb_from_building(self.sample_polygon, 0.0)
        self.assertIsNone(glb_bytes_zero)
        glb_bytes_negative = create_glb_from_building(self.sample_polygon, -10.0)
        self.assertIsNone(glb_bytes_negative)

    # --- Tests for generate_building_tileset ---
    def test_generate_building_tileset_success(self):
        """Test successful generation of a 3D Tiles tileset."""
        sample_data = {
            'id': ['B1', 'B2'],
            'height_val': [20.0, 15.0],
            'geometry': [
                Polygon([(0, 0), (0, 10), (10, 10), (10, 0)]),
                Polygon([(20, 0), (20, 10), (30, 10), (30, 0)])
            ]
        }
        buildings_gdf = gpd.GeoDataFrame(sample_data, crs="EPSG:32632")
        
        success = generate_building_tileset(buildings_gdf, 'height_val', self.test_output_dir)
        self.assertTrue(success)
        
        # Verify tileset.json and B3DM files
        tileset_json_path = os.path.join(self.test_output_dir, "tileset.json")
        self.assertTrue(os.path.exists(tileset_json_path))
        
        tiles_data_path = os.path.join(self.test_output_dir, "tiles")
        self.assertTrue(os.path.exists(tiles_data_path))
        
        # Expect two B3DM files
        b3dm_files = [f for f in os.listdir(tiles_data_path) if f.endswith(".b3dm")]
        self.assertEqual(len(b3dm_files), 2)

        # Validate tileset.json content (Enhancement from subtask)
        with open(tileset_json_path, 'r') as f:
            tileset_data = json.load(f)
        
        self.assertIn("asset", tileset_data)
        self.assertEqual(tileset_data["asset"]["version"], "1.0") # py3dtiles default or 1.1
        self.assertIn("root", tileset_data)
        self.assertIsNotNone(tileset_data["root"])
        self.assertIn("geometricError", tileset_data) # Root geometric error
        self.assertTrue(tileset_data["geometricError"] > 0)
        self.assertIn("boundingVolume", tileset_data["root"])
        self.assertIn("box", tileset_data["root"]["boundingVolume"])

        # Check for children if they are directly under root (flat hierarchy for this simple case)
        self.assertIn("children", tileset_data["root"])
        self.assertEqual(len(tileset_data["root"]["children"]), 2) # One child tile per B3DM
        
        for child_tile in tileset_data["root"]["children"]:
            self.assertIn("content", child_tile)
            self.assertTrue(child_tile["content"]["uri"].startswith("tiles/building_"))
            self.assertTrue(child_tile["content"]["uri"].endswith(".b3dm"))
            self.assertIn("boundingVolume", child_tile)
            self.assertIn("box", child_tile["boundingVolume"])
            self.assertTrue(child_tile["geometricError"] > 0)


    def test_generate_building_tileset_empty_gdf(self):
        """Test tileset generation with an empty GeoDataFrame."""
        empty_gdf = gpd.GeoDataFrame({'id':[], 'height_val':[], 'geometry':[]}, crs="EPSG:32632")
        success = generate_building_tileset(empty_gdf, 'height_val', self.test_output_dir)
        self.assertTrue(success) # Function should still succeed and write a minimal tileset.json
        
        tileset_json_path = os.path.join(self.test_output_dir, "tileset.json")
        self.assertTrue(os.path.exists(tileset_json_path))
        
        # Validate tileset.json for empty case
        with open(tileset_json_path, 'r') as f:
            tileset_data = json.load(f)
        self.assertIn("asset", tileset_data)
        self.assertIn("root", tileset_data)
        self.assertTrue(tileset_data["geometricError"] > 0) # Default geometric error
        # Check if root has no children or if children array is empty
        if "children" in tileset_data["root"]:
            self.assertEqual(len(tileset_data["root"]["children"]), 0)
        else:
            # If no children array, that's also acceptable for an empty tileset root
            pass 


    def test_generate_building_tileset_invalid_heights(self):
        """Test with some buildings having invalid height data."""
        sample_data = {
            'id': ['B1', 'B2', 'B3'],
            'height_val': [20.0, 'invalid', -5.0], # One valid, two invalid
            'geometry': [
                Polygon([(0, 0), (0, 10), (10, 10), (10, 0)]),
                Polygon([(20, 0), (20, 10), (30, 10), (30, 0)]),
                Polygon([(40, 0), (40, 10), (50, 10), (50, 0)])
            ]
        }
        buildings_gdf = gpd.GeoDataFrame(sample_data, crs="EPSG:32632")
        
        success = generate_building_tileset(buildings_gdf, 'height_val', self.test_output_dir)
        self.assertTrue(success)
        
        tiles_data_path = os.path.join(self.test_output_dir, "tiles")
        self.assertTrue(os.path.exists(tiles_data_path))
        b3dm_files = [f for f in os.listdir(tiles_data_path) if f.endswith(".b3dm")]
        self.assertEqual(len(b3dm_files), 1) # Only one building was valid

        # Validate tileset.json content
        tileset_json_path = os.path.join(self.test_output_dir, "tileset.json")
        with open(tileset_json_path, 'r') as f:
            tileset_data = json.load(f)
        self.assertIn("asset", tileset_data)
        self.assertIn("root", tileset_data)
        self.assertIn("children", tileset_data["root"])
        self.assertEqual(len(tileset_data["root"]["children"]), 1)


    # This test requires mocking create_glb_from_building if we want to isolate generate_building_tileset logic
    @patch('skyline_agent.threed_tiles_utils.create_glb_from_building')
    def test_generate_building_tileset_glb_creation_fails_for_all(self, mock_create_glb):
        """Test when all GLB creations fail."""
        mock_create_glb.return_value = None # All GLB creations fail
        sample_data = {
            'id': ['B1'], 'height_val': [20.0],
            'geometry': [Polygon([(0, 0), (0, 10), (10, 10), (10, 0)])]
        }
        buildings_gdf = gpd.GeoDataFrame(sample_data, crs="EPSG:32632")
        
        success = generate_building_tileset(buildings_gdf, 'height_val', self.test_output_dir)
        self.assertTrue(success) # Should still produce a minimal tileset.json
        
        tileset_json_path = os.path.join(self.test_output_dir, "tileset.json")
        self.assertTrue(os.path.exists(tileset_json_path))
        
        with open(tileset_json_path, 'r') as f:
            tileset_data = json.load(f)
        if "children" in tileset_data["root"]:
            self.assertEqual(len(tileset_data["root"]["children"]), 0)


if __name__ == '__main__':
    unittest.main()
