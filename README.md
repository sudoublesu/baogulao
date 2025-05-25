# Skyline Agent

Skyline Agent is a Python-based tool for 3D urban environment analysis. It focuses on visualizing GIS data (buildings, roads, land use) in a 3D scene and recommending optimal building heights for target plots based on surrounding structures.

## Project Structure

*   `skyline_agent/`: Contains the core Python modules for the agent.
    *   `gis_utils.py`: Utilities for loading and handling GIS data.
    *   `visualization_utils.py`: Utilities for creating 3D visualizations using PyVista.
    *   `analysis_utils.py`: Utilities for performing spatial analysis, such as height recommendations.
    *   `main.py`: The main executable script to run the Skyline Agent workflow.
*   `data/`: Intended directory for input GIS data files (e.g., Shapefiles, GeoJSON). **This directory is currently empty. Users need to add their own data files here and update the paths in `skyline_agent/main.py` accordingly.**
*   `skyline_agent/tests/`: Contains unit tests for the agent's modules (currently not implemented in this phase).

## Required Dependencies

The project relies on the following Python libraries:

*   `geopandas`: For loading and manipulating geospatial data.
*   `shapely`: For geometric operations (often a dependency of GeoPandas).
*   `pyvista`: For 3D visualization.
*   `matplotlib`: Used by PyVista as a fallback or for certain plot features.
*   `rtree` (optional): Can improve performance for spatial indexing in GeoPandas.
*   `pygeos` (optional): Can improve performance for vectorized geometric operations in GeoPandas (often a dependency).

You can typically install these using pip:
`pip install geopandas shapely pyvista matplotlib rtree`

## How to Run

1.  **Prepare Your Data:**
    *   Place your GIS data files (e.g., building footprints, road networks, land use polygons) into the `data/` directory. Common formats include Shapefile (`.shp`), GeoJSON (`.geojson`), etc.
    *   **Building Data Requirements:** The building layer must include an attribute (column) specifying the height of each building.
    *   **Land Use Data Requirements:** The land use layer must include an attribute that serves as a unique identifier for each plot if you intend to use the target plot analysis features.

2.  **Configure `main.py`:**
    *   Open `skyline_agent/main.py`.
    *   At the top of the script, update the following placeholder constants to match your data files and attribute names:
        *   `BUILDINGS_FILE_PATH`: Path to your building data file (e.g., `"../data/my_buildings.shp"`).
        *   `ROADS_FILE_PATH`: Path to your roads data file.
        *   `LAND_USE_FILE_PATH`: Path to your land use data file.
        *   `BUILDING_HEIGHT_COLUMN`: The name of the attribute in your building data that stores height values (e.g., `"HEIGHT"` or `"building_h"`).
        *   `LAND_USE_PLOT_ID_COLUMN`: The name of the attribute in your land use data for plot identifiers (e.g., `"PLOT_ID"` or `"parcel_id"`).
        *   `TARGET_PLOT_IDENTIFIER`: The specific ID of the plot you want to analyze (e.g., `"P123"`).

3.  **Run the Script:**
    *   Navigate to the root directory of the project in your terminal.
    *   Execute the main script using:
        ```bash
        python skyline_agent/main.py
        ```

## Output

The Skyline Agent produces the following outputs:

1.  **Console Output:**
    *   Status messages indicating the progress of data loading, analysis, and visualization.
    *   If a target plot is identified and analysis is successful, a message with the recommended building height for that plot (e.g., "Recommended height for plot 'PlotA123': 25.50 units").
    *   Warnings or error messages if issues are encountered (e.g., files not found, missing data attributes).

2.  **3D Interactive Visualization:**
    *   A PyVista plot window displaying the 3D scene, which includes:
        *   Extruded building meshes, colored and with edges highlighted.
        *   Height labels displayed above each building.
        *   Road network lines.
        *   Land use polygons.
        *   The target plot (if identified) is highlighted with a distinct style (e.g., red wireframe).
    *   The plot window is interactive, allowing you to zoom, pan, and rotate the camera.
    *   Axes are displayed to aid orientation.

Close the PyVista window to terminate the script.