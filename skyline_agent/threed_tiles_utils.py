import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon
import trimesh
import io
import os # Added
import json # Added
import logging

# py3dtiles imports - adjust specific classes based on API
# From py3dtiles documentation and examples, common usage involves:
# from py3dtiles.tileset.tile import Tile
# from py3dtiles.tileset.content import B3dm
# from py3dtiles.tileset.bounding_volume import BoundingBox
# from py3dtiles.tileset.main import TileSet
# Let's try to use these, or adjust if the API has changed / common practice is different
from py3dtiles.tileset.tile import Tile
from py3dtiles.tileset.content.b3dm import B3dm # More specific path for B3dm
from py3dtiles.tileset.bounding_volume import BoundingBox # For bounding volumes
from py3dtiles.tileset.main import TileSet # Main TileSet class
# Note: py3dtiles.Glb seems to be a utility for reading GLB, not for direct use in B3dm as of some versions.
# B3dm objects usually take glb *bytes*.


# Configure basic logging
logging.basicConfig(level=logging.INFO) # Ensure this is not duplicated if already set elsewhere
logger = logging.getLogger(__name__)

def create_glb_from_building(building_polygon: Polygon, height: float, attributes: dict = None) -> bytes | None:
    """
    Creates a GLB (binary glTF) representation of a 3D building from its footprint and height.

    Args:
        building_polygon: A Shapely Polygon representing the 2D building footprint.
        height: The height of the building.
        attributes: Optional dictionary of attributes to store in the mesh metadata.

    Returns:
        Bytes of the GLB file, or None if an error occurred.
    """
    if not isinstance(building_polygon, Polygon):
        logger.warning("Invalid building_polygon: Not a Shapely Polygon.")
        return None
    if not building_polygon.is_valid:
        logger.warning(f"Invalid building_polygon: Geometry is not valid ({building_polygon.is_valid_reason}).")
        return None
    if height <= 0:
        logger.warning(f"Invalid height: {height}. Height must be positive.")
        return None

    try:
        # --- Vertex Generation ---
        # Get exterior coordinates, removing the duplicate end coordinate
        exterior_coords = np.array(building_polygon.exterior.coords)
        if len(exterior_coords) < 4: # Need at least 3 unique points for a polygon (plus duplicate end point)
            logger.warning(f"Building polygon has too few points: {len(exterior_coords)} (including duplicate end point). Needs at least 3 unique points.")
            return None
        
        unique_coords = exterior_coords[:-1, :] # All points except the last one (which is a duplicate of the first)
        num_points = unique_coords.shape[0]

        if num_points < 3:
            logger.warning(f"Building polygon has too few unique points: {num_points}. Needs at least 3.")
            return None

        bottom_vertices_np = np.hstack((unique_coords, np.zeros((num_points, 1))))
        top_vertices_np = np.hstack((unique_coords, np.full((num_points, 1), height)))
        
        # Combine all vertices: bottom first, then top
        all_vertices_np = np.vstack((bottom_vertices_np, top_vertices_np))

        # --- Face Generation ---
        faces = []

        # Wall faces
        for i in range(num_points):
            # Current bottom vertex index: i
            # Next bottom vertex index: (i + 1) % num_points (to loop back to the start)
            # Current top vertex index: i + num_points
            # Next top vertex index: (i + 1) % num_points + num_points
            
            p0 = i                                  # bottom_vertices[i]
            p1 = (i + 1) % num_points               # bottom_vertices[i+1]
            p2 = (i + 1) % num_points + num_points  # top_vertices[i+1]
            p3 = i + num_points                     # top_vertices[i]

            # Triangle 1: p0, p1, p2 (e.g., bottom_i, bottom_i+1, top_i+1)
            faces.append([p0, p1, p2])
            # Triangle 2: p0, p2, p3 (e.g., bottom_i, top_i+1, top_i)
            faces.append([p0, p2, p3])

        # Floor face (triangulation of the bottom polygon)
        # For simple convex polygons, trimesh can often infer this, but explicit is better.
        # Trimesh's triangulate_polygon operates on 2D points.
        # The floor vertices are 0 to num_points-1
        if num_points >= 3:
            # Triangulate the 2D footprint
            floor_triangles = trimesh.creation.triangulate_polygon(unique_coords, triangle_args='pq0.1') # 'q' for quality, 'p' for planar, '0.1' for min angle
            for tri in floor_triangles:
                # Ensure correct winding order for downward-facing normal (clockwise)
                # or adjust normals later. Default trimesh winding is usually CCW for outward.
                # For floor (viewed from outside), it should be CW.
                faces.append([tri[2], tri[1], tri[0]]) # Reverse order for CW

        # Roof face (triangulation of the top polygon)
        # The roof vertices are num_points to 2*num_points-1
        if num_points >= 3:
            roof_triangles = trimesh.creation.triangulate_polygon(unique_coords, triangle_args='pq0.1')
            for tri in roof_triangles:
                # Add num_points to each index to map to top vertices
                # Keep CCW order for upward-facing normal
                faces.append([tri[0] + num_points, tri[1] + num_points, tri[2] + num_points])
        
        faces_np = np.array(faces)

        # --- Trimesh Object ---
        mesh = trimesh.Trimesh(vertices=all_vertices_np, faces=faces_np)

        # Check if the mesh is watertight and fix if not, if possible
        if not mesh.is_watertight:
            logger.info(f"Mesh for building (polygon with {num_points} points, height {height}) is not watertight. Attempting to fill holes.")
            mesh.fill_holes() # This might not always work perfectly
            if not mesh.is_watertight:
                 logger.warning(f"Mesh for building (polygon with {num_points} points, height {height}) could not be made watertight after fill_holes.")
            else:
                 logger.info(f"Mesh for building (polygon with {num_points} points, height {height}) successfully made watertight.")


        # Assign attributes if provided
        if attributes:
            if not hasattr(mesh, 'metadata'):
                mesh.metadata = {}
            mesh.metadata.update(attributes)
            # Alternative: mesh.geometry.metadata for specific geometry attributes,
            # but trimesh.Trimesh.metadata is simpler for general key-value.

        # --- Export to GLB ---
        # Using export method directly on the mesh object
        glb_data = mesh.export(file_type='glb')
        
        # # Alternative using trimesh.exchange.gltf:
        # # glb_data = trimesh.exchange.gltf.export_glb(mesh, include_normals=True) 
        # # include_normals=True is often default or handled by trimesh

        logger.info(f"Successfully created GLB for building (polygon with {num_points} points, height {height}). Size: {len(glb_data)} bytes.")
        return glb_data

    except Exception as e:
        logger.error(f"Error creating GLB for building (polygon with {building_polygon.wkt[:50]}..., height {height}): {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Example Usage (simple test case)
    print("Running basic test for create_glb_from_building...")
    
    # 1. Create a sample square polygon
    square_poly = Polygon([(0, 0), (0, 10), (10, 10), (10, 0)])
    building_height = 20.0
    building_attrs = {"name": "Test Building", "id": 123}

    print(f"Polygon: {square_poly.wkt}, Height: {building_height}")
    glb_bytes = create_glb_from_building(square_poly, building_height, building_attrs)

    if glb_bytes:
        print(f"GLB created successfully. Size: {len(glb_bytes)} bytes.")
        # You could save this to a file to inspect:
        # with open("test_building.glb", "wb") as f:
        #     f.write(glb_bytes)
        # print("Saved to test_building.glb")
    else:
        print("Failed to create GLB.")

    print("\nTesting with a more complex polygon (L-shape)...")
    l_shape_poly = Polygon([(0,0), (0,20), (10,20), (10,10), (20,10), (20,0)])
    l_height = 15.0
    glb_bytes_l = create_glb_from_building(l_shape_poly, l_height, {"type": "L-shape"})
    if glb_bytes_l:
        print(f"L-shape GLB created successfully. Size: {len(glb_bytes_l)} bytes.")
        # with open("l_shape_building.glb", "wb") as f:
        #     f.write(glb_bytes_l)
        # print("Saved to l_shape_building.glb")
    else:
        print("Failed to create L-shape GLB.")

    print("\nTesting with an invalid polygon (too few points)...")
    line_poly = Polygon([(0,0), (0,10)]) # This is actually a LineString, Polygon would make it from this
    try:
        # Shapely Polygon constructor might make a valid polygon if it can close it
        # Let's make one that is definitely too simple
        invalid_poly_coords = [(0,0), (1,1)] # Only 2 points
        # building_polygon.exterior.coords requires at least 3 points (start, one point, end=start)
        # So a valid polygon needs at least 3 unique points.
        # Trimesh triangulation will fail for less than 3 points.
        # The check `len(exterior_coords) < 4` (i.e. <3 unique points) handles this.
        
        # Test directly with a known invalid polygon structure for the function
        # (though shapely might try to fix it or deem it invalid)
        
        # exterior_coords = np.array(invalid_poly_coords) # This would fail earlier
        # Forcing a Polygon object that might be invalid or too simple
        
        # Test case for a polygon that becomes valid but has too few points after unique extraction
        degenerate_poly = Polygon([(0,0), (1,1), (0,0)]) # 2 unique points
        glb_bytes_degen = create_glb_from_building(degenerate_poly, 10.0)
        if glb_bytes_degen:
             print(f"Degenerate GLB created? Size: {len(glb_bytes_degen)} bytes. This might indicate an issue if it shouldn't pass.")
        else:
            print("Degenerate GLB creation failed as expected (or due to other error).")


    except Exception as e:
        print(f"Error during invalid polygon test setup: {e}")


    print("\nTesting with zero height...")
    glb_zero_h = create_glb_from_building(square_poly, 0)
    if glb_zero_h:
        print(f"Zero height GLB created? Size: {len(glb_zero_h)} bytes.")
    else:
        print("Zero height GLB creation failed as expected.")

    print("\nTesting with non-Polygon input...")
    from shapely.geometry import Point
    glb_point_input = create_glb_from_building(Point(0,0), 10)
    if glb_point_input:
        print(f"Point input GLB created? Size: {len(glb_point_input)} bytes.")
    else:
        print("Point input GLB creation failed as expected.")
        
    print("\nBasic tests completed.")


def generate_building_tileset(buildings_gdf: gpd.GeoDataFrame, 
                              height_column: str, 
                              output_dir: str, 
                              tileset_filename: str = "tileset.json") -> bool:
    """
    Generates a 3D Tiles tileset from building GeoDataFrame.

    Each building is converted to a GLB, then packaged into a B3DM tile.
    A single root tile contains all building B3DM tiles as children.

    Args:
        buildings_gdf: GeoDataFrame containing building polygons and heights.
        height_column: Name of the column in buildings_gdf with height values.
        output_dir: The directory where the tileset and tile data will be saved.
        tileset_filename: Filename for the main tileset JSON file.

    Returns:
        True if the tileset generation was successful, False otherwise.
    """
    try:
        # --- Setup Output Directory ---
        tiles_data_dir = os.path.join(output_dir, "tiles")
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(tiles_data_dir, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Tiles data directory: {tiles_data_dir}")

        # --- Initialize Tileset ---
        ts = TileSet()
        
        all_tile_bounding_boxes = [] # To compute root bounding box

        # --- Iterate Through Buildings ---
        for index, building in buildings_gdf.iterrows():
            building_polygon = building.geometry
            building_id = building.get('id', index) # Use 'id' column if exists, else index

            try:
                height = float(building[height_column])
                if height <= 0:
                    logger.warning(f"Building ID {building_id} at index {index} has non-positive height ({height}). Skipping.")
                    continue
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Could not get valid height for building ID {building_id} at index {index} from column '{height_column}'. Error: {e}. Skipping.")
                continue

            # Generate GLB
            attributes = {'id': building_id, 'original_index': index}
            if 'name' in building: # Example of adding more attributes
                 attributes['name'] = building['name']
            
            glb_bytes = create_glb_from_building(building_polygon, height, attributes=attributes)

            if not glb_bytes:
                logger.warning(f"Failed to generate GLB for building ID {building_id} at index {index}. Skipping.")
                continue

            # --- Create B3DM Tile from GLB ---
            b3dm_tile_content = B3dm.from_glb(glb_bytes) # py3dtiles can take GLB bytes directly
            
            # Save B3DM tile content to file
            b3dm_filename = f"building_{index}.b3dm" # Unique filename based on index
            b3dm_filepath = os.path.join(tiles_data_dir, b3dm_filename)
            
            try:
                with open(b3dm_filepath, 'wb') as f:
                    f.write(b3dm_tile_content.to_array()) # .to_array() gets the bytes for the b3dm
                logger.info(f"Saved B3DM tile: {b3dm_filepath} ({len(b3dm_tile_content.to_array())} bytes)")
            except Exception as e:
                logger.error(f"Failed to write B3DM tile {b3dm_filepath} for building ID {building_id}. Error: {e}", exc_info=True)
                continue


            # --- Create Tile Object ---
            tile = Tile()
            tile.content_uri = os.path.join("tiles", b3dm_filename) # Relative path

            # Bounding Volume for the individual tile
            minx, miny, maxx, maxy = building_polygon.bounds
            center_x = (minx + maxx) / 2.0
            center_y = (miny + maxy) / 2.0
            center_z = height / 2.0
            
            extent_x = (maxx - minx) / 2.0
            extent_y = (maxy - miny) / 2.0
            extent_z = height / 2.0

            # py3dtiles box format: [center_x, center_y, center_z, extent_x, 0, 0, 0, extent_y, 0, 0, 0, extent_z]
            # These are the diagonal elements of the half-axis matrix.
            box_array = [
                center_x, center_y, center_z, 
                extent_x, 0, 0, 
                0, extent_y, 0, 
                0, 0, extent_z
            ]
            tile.bounding_volume = BoundingBox.from_list(box_array)
            all_tile_bounding_boxes.append(box_array)


            # Geometric Error (example: diagonal of the footprint bounding box)
            # This is a placeholder; more sophisticated calculation might be needed for LODs.
            geometric_error = np.sqrt((maxx - minx)**2 + (maxy - miny)**2) / 10.0 # Heuristic
            tile.geometric_error = geometric_error if geometric_error > 0 else 1.0

            # Add to tileset's root tile's children
            ts.add_tile(tile) # Adds to root by default if root is empty, or can manage hierarchy

        if not ts.tiles: # Check if any tiles were added
            logger.warning("No building tiles were successfully generated. Tileset will be empty or minimal.")
            # Still save a minimal tileset.json for consistency, or return False?
            # For now, proceed to write a potentially empty tileset.

        # --- Finalize Tileset (Root Tile Bounding Volume and Geometric Error) ---
        if all_tile_bounding_boxes:
            # Combine all individual bounding boxes to create a root bounding box
            all_boxes_np = np.array([b[:3] for b in all_tile_bounding_boxes]) # Centers
            all_extents_np = np.array([b[3:12] for b in all_tile_bounding_boxes]) # Half-axes matrices (simplified here for extent calculation)

            min_coords = np.min(all_boxes_np - np.array([b[3] for b in all_tile_bounding_boxes])[:, np.newaxis] * np.array([1,0,0,0,1,0,0,0,1])[:3] , axis=0) # Incorrect calculation for extent
            max_coords = np.max(all_boxes_np + np.array([b[3] for b in all_tile_bounding_boxes])[:, np.newaxis] * np.array([1,0,0,0,1,0,0,0,1])[:3] , axis=0) # Incorrect calculation for extent
            
            # Correct way to calculate overall bounding box from individual boxes:
            # Find min/max of (center - extent) and (center + extent) for each axis
            min_overall_x = min(b[0] - b[3] for b in all_tile_bounding_boxes)
            min_overall_y = min(b[1] - b[7] for b in all_tile_bounding_boxes) # b[7] is extent_y
            min_overall_z = min(b[2] - b[11] for b in all_tile_bounding_boxes) # b[11] is extent_z
            
            max_overall_x = max(b[0] + b[3] for b in all_tile_bounding_boxes)
            max_overall_y = max(b[1] + b[7] for b in all_tile_bounding_boxes)
            max_overall_z = max(b[2] + b[11] for b in all_tile_bounding_boxes)

            root_center_x = (min_overall_x + max_overall_x) / 2.0
            root_center_y = (min_overall_y + max_overall_y) / 2.0
            root_center_z = (min_overall_z + max_overall_z) / 2.0
            
            root_extent_x = (max_overall_x - min_overall_x) / 2.0
            root_extent_y = (max_overall_y - min_overall_y) / 2.0
            root_extent_z = (max_overall_z - min_overall_z) / 2.0

            root_box_array = [
                root_center_x, root_center_y, root_center_z,
                root_extent_x, 0, 0,
                0, root_extent_y, 0,
                0, 0, root_extent_z
            ]
            ts.bounding_volume = BoundingBox.from_list(root_box_array)
            # Geometric error for the root tile: usually larger, e.g., diagonal of the entire dataset
            ts.geometric_error = np.sqrt(root_extent_x**2 + root_extent_y**2 + root_extent_z**2) * 2 # Full diagonal
        else:
            # Default bounding box if no tiles (e.g. center 0,0,0, extent 1,1,1)
            ts.bounding_volume = BoundingBox.from_list([0,0,0, 1,0,0, 0,1,0, 0,0,1])
            ts.geometric_error = 100 # Arbitrary large error

        # Set a default transform for the tileset if CRS is known (e.g. to WGS84)
        # For now, assume coordinates are in a local Cartesian system.
        # ts.asset.extras = {"crs": buildings_gdf.crs.to_string()} if buildings_gdf.crs else {}


        # --- Write Tileset File ---
        tileset_path = os.path.join(output_dir, tileset_filename)
        ts.write_to_file(tileset_path)
        logger.info(f"Tileset written to {tileset_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to generate tileset: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    # Example Usage for generate_building_tileset (requires sample data)
    print("\nRunning basic test for generate_building_tileset...")

    # Create a sample GeoDataFrame
    sample_data = {
        'id': [1, 2, 'building3'],
        'height': [20.0, 15.0, 25.5],
        'name': ['Building A', 'Building B', 'Building C'],
        'geometry': [
            Polygon([(0, 0), (0, 10), (10, 10), (10, 0)]),
            Polygon([(20, 20), (20, 30), (30, 30), (30, 20)]),
            Polygon([(0, 20), (0, 30), (5, 30), (5,25), (10,25), (10,20)]) # L-shape like
        ]
    }
    sample_gdf = gpd.GeoDataFrame(sample_data, crs="EPSG:32632") # Example CRS

    output_directory = "sample_tileset_output" 
    
    # Clean up previous run if any
    if os.path.exists(output_directory):
        import shutil
        shutil.rmtree(output_directory)
        print(f"Cleaned up previous output directory: {output_directory}")

    success = generate_building_tileset(sample_gdf, 'height', output_directory)

    if success:
        print(f"Tileset generation test completed successfully. Output in: {output_directory}")
        # Verify by checking for tileset.json and tiles/building_*.b3dm files
        if os.path.exists(os.path.join(output_directory, "tileset.json")):
            print("tileset.json found.")
        else:
            print("ERROR: tileset.json NOT found.")
        
        tiles_dir = os.path.join(output_directory, "tiles")
        if os.path.exists(tiles_dir) and len(os.listdir(tiles_dir)) == 3 : # Expect 3 b3dm files
             print(f"Found {len(os.listdir(tiles_dir))} files in tiles directory: {os.listdir(tiles_dir)}")
        else:
            print(f"ERROR: Tiles directory ({tiles_dir}) missing or incorrect number of files.")

    else:
        print("Tileset generation test failed.")
    
    print("\nTesting with an empty GeoDataFrame...")
    empty_gdf = gpd.GeoDataFrame({'id':[], 'height':[], 'geometry':[]}, crs="EPSG:32632")
    output_empty_dir = "sample_tileset_empty_output"
    if os.path.exists(output_empty_dir):
        import shutil
        shutil.rmtree(output_empty_dir)
        print(f"Cleaned up previous output directory: {output_empty_dir}")

    success_empty = generate_building_tileset(empty_gdf, 'height', output_empty_dir)
    if success_empty:
        print(f"Empty GDF Tileset generation test completed. Output in: {output_empty_dir}")
        if os.path.exists(os.path.join(output_empty_dir, "tileset.json")):
            print("tileset.json found for empty GDF.")
        else:
            print("ERROR: tileset.json NOT found for empty GDF.")
        tiles_dir_empty = os.path.join(output_empty_dir, "tiles")
        if os.path.exists(tiles_dir_empty) and not os.listdir(tiles_dir_empty):
             print(f"Tiles directory for empty GDF is correctly empty.")
        else:
            print(f"ERROR: Tiles directory for empty GDF ({tiles_dir_empty}) has files or is missing.")
    else:
        print("Empty GDF Tileset generation test failed (this might be okay if it returns False as expected for no tiles).")


    print("\nTesting with GDF with invalid height data...")
    invalid_height_data = {
        'id': [1, 2, 3],
        'height': [20.0, 'error', -5.0], # one valid, one error, one non-positive
        'geometry': [
            Polygon([(0, 0), (0, 10), (10, 10), (10, 0)]),
            Polygon([(20, 20), (20, 30), (30, 30), (30, 20)]),
            Polygon([(0, 20), (0, 30), (10, 30), (10,20)])
        ]
    }
    invalid_height_gdf = gpd.GeoDataFrame(invalid_height_data, crs="EPSG:32632")
    output_invalid_dir = "sample_tileset_invalid_output"
    if os.path.exists(output_invalid_dir):
        import shutil
        shutil.rmtree(output_invalid_dir)
        print(f"Cleaned up previous output directory: {output_invalid_dir}")
    
    success_invalid = generate_building_tileset(invalid_height_gdf, 'height', output_invalid_dir)
    if success_invalid:
        print(f"Invalid Height GDF Tileset generation test completed. Output in: {output_invalid_dir}")
        tiles_dir_invalid = os.path.join(output_invalid_dir, "tiles")
        # Expect 1 b3dm file for the one valid building
        if os.path.exists(tiles_dir_invalid) and len(os.listdir(tiles_dir_invalid)) == 1 :
             print(f"Found {len(os.listdir(tiles_dir_invalid))} file in tiles directory as expected: {os.listdir(tiles_dir_invalid)}")
        else:
            print(f"ERROR: Tiles directory ({tiles_dir_invalid}) missing or incorrect number of files (expected 1). Found: {os.listdir(tiles_dir_invalid) if os.path.exists(tiles_dir_invalid) else 'None'}")
    else:
        print("Invalid Height GDF Tileset generation test failed.")
