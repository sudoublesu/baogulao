import geopandas as gpd
from shapely.geometry.base import BaseGeometry
import numpy as np # For nanmean if needed, or just manual handling

def get_target_plot(land_use_gdf: gpd.GeoDataFrame, plot_id_column: str, target_plot_id) -> BaseGeometry | None:
    """
    Filters a GeoDataFrame to find a specific plot by its ID and returns its geometry.

    Args:
        land_use_gdf: GeoDataFrame containing land use plots.
        plot_id_column: The name of the column in land_use_gdf that contains unique plot identifiers.
        target_plot_id: The identifier of the specific plot to find.

    Returns:
        A Shapely geometry object of the target plot if found, otherwise None.
    """
    try:
        target_plot_series = land_use_gdf[land_use_gdf[plot_id_column] == target_plot_id]
        if target_plot_series.empty:
            print(f"Warning: Plot with ID '{target_plot_id}' not found in column '{plot_id_column}'.")
            return None
        # Return the geometry of the first match (assuming IDs are unique)
        return target_plot_series.geometry.iloc[0] # Return the actual geometry object
    except KeyError:
        print(f"Warning: Column '{plot_id_column}' not found in the land_use GeoDataFrame.")
        return None
    except Exception as e:
        print(f"An error occurred while trying to get the target plot: {e}")
        return None

def recommend_building_height(target_plot_geometry: BaseGeometry | gpd.GeoSeries, 
                              surrounding_buildings_gdf: gpd.GeoDataFrame, 
                              height_column: str, 
                              buffer_distance: float = 50.0) -> float | None:
    """
    Recommends a building height based on the average height of surrounding buildings within a buffer.

    Args:
        target_plot_geometry: Shapely geometry object or GeoSeries of the target plot.
        surrounding_buildings_gdf: GeoDataFrame of buildings with height information.
        height_column: The name of the column in surrounding_buildings_gdf containing heights.
        buffer_distance: Distance (in the units of the GDF's CRS) to create a buffer 
                         around the target plot to find surrounding buildings.

    Returns:
        The average height of surrounding buildings, or None if no buildings are found
        or no valid height data is available.
    """
    if target_plot_geometry is None:
        print("Warning: Target plot geometry is None. Cannot recommend height.")
        return None

    # If target_plot_geometry is a GeoSeries, extract the geometry object
    if isinstance(target_plot_geometry, gpd.GeoSeries):
        if target_plot_geometry.empty:
            print("Warning: Target plot GeoSeries is empty. Cannot recommend height.")
            return None
        actual_geometry = target_plot_geometry.iloc[0] # Use the first geometry
    elif isinstance(target_plot_geometry, BaseGeometry):
        actual_geometry = target_plot_geometry
    else:
        print(f"Warning: target_plot_geometry is of an unsupported type: {type(target_plot_geometry)}. Cannot recommend height.")
        return None

    if not isinstance(actual_geometry, BaseGeometry):
        print(f"Warning: Extracted actual_geometry is not a valid Shapely geometry. Got {type(actual_geometry)}. Cannot recommend height.")
        return None

    try:
        buffer_polygon = actual_geometry.buffer(buffer_distance)
    except Exception as e:
        print(f"Error creating buffer for target plot geometry: {e}")
        return None

    try:
        # Ensure the GDF has a valid geometry column
        if not hasattr(surrounding_buildings_gdf, 'geometry') or surrounding_buildings_gdf.geometry.name not in surrounding_buildings_gdf.columns:
            print("Warning: surrounding_buildings_gdf does not have a valid geometry column.")
            return None
            
        # Filter buildings that intersect the buffer
        # Use spatial index if available for performance (rtree needs to be installed)
        # Check if GDF is empty before attempting spatial indexing or intersection
        if surrounding_buildings_gdf.empty:
            print("Warning: surrounding_buildings_gdf is empty. No buildings to compare.")
            return None

        # Ensure a spatial index exists for faster intersection, if not, geopandas creates one on the fly
        # but it can be slow for large datasets.
        # Forcing creation: if not surrounding_buildings_gdf.sindex: surrounding_buildings_gdf.sindex
        
        nearby_buildings = surrounding_buildings_gdf[surrounding_buildings_gdf.intersects(buffer_polygon)]
    except Exception as e:
        print(f"Error filtering buildings by intersection: {e}")
        return None
        
    if nearby_buildings.empty:
        print(f"Warning: No buildings found within {buffer_distance} units of the target plot.")
        return None

    if height_column not in nearby_buildings.columns:
        print(f"Warning: Height column '{height_column}' not found in surrounding buildings GeoDataFrame.")
        return None

    heights = []
    for h_val in nearby_buildings[height_column]:
        try:
            numeric_height = float(h_val)
            if numeric_height > 0: # Consider only positive heights
                heights.append(numeric_height)
            else:
                print(f"Warning: Non-positive height value '{h_val}' found. Skipping.")
        except (ValueError, TypeError):
            print(f"Warning: Could not convert height value '{h_val}' to numeric. Skipping.")
            continue
            
    if not heights:
        print("Warning: No valid building heights found for nearby buildings.")
        return None
        
    average_height = sum(heights) / len(heights)
    return average_height
