# main.py
"""
Main script for the Skyline Agent to load, analyze, and visualize 3D urban data.
"""

import pyvista as pv
from .gis_utils import load_buildings, load_roads, load_land_use
from .visualization_utils import setup_plotter, add_buildings_to_plotter, add_geodataframe_to_plotter, add_height_labels_to_plotter
from .analysis_utils import get_target_plot, recommend_building_height
import geopandas as gpd # For creating an empty GeoDataFrame if needed for target_plot_geom visualization

# --- Configuration Parameters ---
# These would ideally be loaded from a config file or command-line arguments
BUILDINGS_FILE_PATH = "../data/sample_buildings.shp"
ROADS_FILE_PATH = "../data/sample_roads.shp"
LAND_USE_FILE_PATH = "../data/sample_land_use.shp"
BUILDING_HEIGHT_COLUMN = "height"  # Attribute name for building height
LAND_USE_PLOT_ID_COLUMN = "plot_ID" # Attribute name for land use plot identifier
TARGET_PLOT_IDENTIFIER = "PlotA123" # Example ID of the plot for analysis

def main():
    """
    Main function to run the Skyline Agent workflow.
    Loads data, performs analysis, and visualizes the scene.
    """
    print("Starting Skyline Agent...")

    # --- 1. Load Data ---
    print("Loading data...")
    buildings_gdf = load_buildings(BUILDINGS_FILE_PATH)
    roads_gdf = load_roads(ROADS_FILE_PATH)
    land_use_gdf = load_land_use(LAND_USE_FILE_PATH)

    # Basic checks for data loading
    if buildings_gdf is None or buildings_gdf.empty:
        print(f"Error: Critical data missing. Failed to load buildings from: {BUILDINGS_FILE_PATH}")
        # Decide if to proceed or exit. For visualization, we might proceed with what we have.
        # For analysis involving buildings, we might need to exit or handle differently.
    if roads_gdf is None or roads_gdf.empty:
        print(f"Warning: Failed to load roads from: {ROADS_FILE_PATH}. Proceeding without roads.")
    if land_use_gdf is None or land_use_gdf.empty:
        print(f"Error: Critical data missing. Failed to load land use data from: {LAND_USE_FILE_PATH}")
        # Similar to buildings, decide if to exit or how to handle.

    # --- 2. Perform Analysis ---
    print("\nPerforming analysis...")
    target_plot_geom = None # Initialize
    recommended_height = None # Initialize

    if land_use_gdf is not None and not land_use_gdf.empty:
        target_plot_geom = get_target_plot(land_use_gdf, LAND_USE_PLOT_ID_COLUMN, TARGET_PLOT_IDENTIFIER)
        
        if target_plot_geom is not None:
            print(f"Target plot '{TARGET_PLOT_IDENTIFIER}' found.")
            if buildings_gdf is not None and not buildings_gdf.empty:
                recommended_height = recommend_building_height(
                    target_plot_geom, 
                    buildings_gdf, 
                    BUILDING_HEIGHT_COLUMN
                )
                if recommended_height is not None:
                    print(f"Recommended height for plot '{TARGET_PLOT_IDENTIFIER}': {recommended_height:.2f} units")
                else:
                    print(f"Could not recommend a height for plot '{TARGET_PLOT_IDENTIFIER}'.")
            else:
                print("Building data is missing, cannot recommend height.")
        else:
            print(f"Target plot '{TARGET_PLOT_IDENTIFIER}' not found in land use data.")
    else:
        print("Land use data is missing, cannot perform plot-specific analysis.")

    # --- 3. Create Visualization ---
    print("\nCreating visualization...")
    plotter = setup_plotter()

    # Add buildings
    if buildings_gdf is not None and not buildings_gdf.empty:
        print("Adding buildings to plotter...")
        add_buildings_to_plotter(plotter, buildings_gdf, BUILDING_HEIGHT_COLUMN, color='tan', opacity=0.9)
        add_height_labels_to_plotter(plotter, buildings_gdf, BUILDING_HEIGHT_COLUMN, font_size=8)
    else:
        print("No building data to visualize.")

    # Add roads
    if roads_gdf is not None and not roads_gdf.empty:
        print("Adding roads to plotter...")
        add_geodataframe_to_plotter(plotter, roads_gdf, color='dimgrey', line_width=2, opacity=0.8)
    else:
        print("No road data to visualize.")

    # Add land use
    if land_use_gdf is not None and not land_use_gdf.empty:
        print("Adding land use to plotter...")
        add_geodataframe_to_plotter(plotter, land_use_gdf, color='lightgreen', opacity=0.4)
    else:
        print("No land use data to visualize.")

    # Highlight the target plot if found
    if target_plot_geom is not None:
        print(f"Highlighting target plot '{TARGET_PLOT_IDENTIFIER}'...")
        try:
            # Ensure target_plot_geom is a single Shapely geometry
            # get_target_plot returns a geometry object directly, so it should be fine
            # If it were a GeoSeries, you'd do target_plot_geom.iloc[0] or similar
            plotter.add_mesh(target_plot_geom, color='red', style='wireframe', line_width=3, opacity=0.7)
            
            # Optionally, add a label for the target plot itself
            centroid = target_plot_geom.centroid
            plotter.add_point_labels(
                [centroid.x, centroid.y, 0.1], # Slightly above ground
                [f"Target: {TARGET_PLOT_IDENTIFIER}"],
                font_size=12,
                text_color='red',
                shape_opacity=0, # Make the point itself invisible
                show_points=False
            )

        except Exception as e:
            print(f"Error adding target plot to visualization: {e}")
            print("This might happen if the geometry is not suitable for direct PyVista mesh creation (e.g. Point).")


    # --- 4. Show Plot ---
    print("\nShowing plot. Close the window to exit.")
    plotter.enable_zoom_scaling()
    plotter.add_axes()
    plotter.show(title="Skyline Agent 3D Visualization")

    print("Skyline Agent finished.")

if __name__ == '__main__':
    main()
