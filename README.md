# Skyline Agent: 3D Urban Analysis & Visualization Service

Skyline Agent is a Python-based backend service designed to process geospatial (GIS) data, generate 3D Tiles for web-based visualization (e.g., in CesiumJS), and provide building height analysis through an HTTP API. It enables dynamic creation of 3D urban scenes and analytical insights from user-provided datasets.

## System Architecture

The project is structured into several core modules:

*   **`skyline_agent/`**: Contains the primary Python modules for the agent.
    *   `gis_utils.py`: Provides utility functions for loading and handling various GIS data formats (e.g., Shapefiles, GeoJSON) using GeoPandas.
    *   `analysis_utils.py`: Contains logic for performing spatial analysis, primarily focused on recommending optimal building heights for specified land use plots based on surrounding building characteristics.
    *   `threed_tiles_utils.py`: Responsible for converting 2D building footprint data (with height attributes) into 3D models (GLB format) and packaging them into 3D Tiles format (`.b3dm` tiles and `tileset.json`) for streaming and rendering in WebGIS platforms.
    *   `api_server.py`: Implements the FastAPI application that exposes HTTP endpoints for interacting with the Skyline Agent. It orchestrates data loading, analysis, and 3D Tiles generation, serving the results to clients.
*   `data/`: Intended directory for input GIS data files. Sample data might be provided here. **Users typically need to add their own data files and reference them in API calls.**
*   `static/`: This directory is created automatically by the API server and is used to store and serve the generated 3D Tilesets.
    *   `static/tilesets/`: Contains subdirectories for each generated tileset.
*   `skyline_agent/tests/`: Contains unit tests for the agent's modules.

## Required Dependencies

The project relies on the following Python libraries:

*   **Core Processing & GIS:**
    *   `geopandas`: For loading and manipulating geospatial data.
    *   `shapely`: For geometric operations (often a dependency of GeoPandas).
    *   `numpy`: For numerical operations, especially in 3D geometry generation.
*   **3D Modeling & Tileset Generation:**
    *   `trimesh`: For creating and manipulating 3D meshes (e.g., extruding building footprints, exporting to GLB).
    *   `pygltflib`: (Potentially used by `trimesh` or directly) For handling glTF/GLB file structures.
    *   `py3dtiles`: For constructing 3D Tiles tilesets (`.b3dm` files and `tileset.json`).
*   **API Server:**
    *   `fastapi`: For building the high-performance HTTP API.
    *   `uvicorn[standard]`: For running the FastAPI application as an ASGI server.
    *   `python-multipart`: For handling form data, often useful with file uploads (though not the primary mode for this API's GET endpoint).
*   **Optional Performance Boosters for GeoPandas:**
    *   `rtree`: Can improve performance for spatial indexing.
    *   `pygeos`: Can improve performance for vectorized geometric operations.

You can typically install these using pip:
```bash
pip install geopandas shapely numpy trimesh pygltflib py3dtiles fastapi "uvicorn[standard]" python-multipart rtree
```
(Consider creating a `requirements.txt` file for easier installation).

## API Documentation

The Skyline Agent provides the following HTTP API endpoint:

### GET `/scene_data/`

**Description:**
This endpoint processes GIS data to generate a 3D Tiles tileset for building visualization and provides a height recommendation for a specified target plot. The generated tileset is stored on the server and its URL is returned.

**Query Parameters:**

| Parameter            | Default Value                   | Description                                                                 |
| -------------------- | ------------------------------- | --------------------------------------------------------------------------- |
| `buildings_file`     | `data/sample_buildings.shp`     | Path to the building footprints data file (relative to project root).       |
| `roads_file`         | `data/sample_roads.shp`         | Path to the road network data file (relative to project root). *(Currently not used in 3D tiles generation but available for future use)* |
| `land_use_file`      | `data/sample_land_use.shp`      | Path to the land use data file (relative to project root).                  |
| `height_column`      | `height`                        | Name of the attribute in `buildings_file` that stores building height values. |
| `plot_id_column`     | `plot_ID`                       | Name of the attribute in `land_use_file` for unique plot identifiers.       |
| `target_plot_id`     | `PlotA123`                      | The specific ID of the plot (from `land_use_file`) for height recommendation. |

**Success Response (200 OK):**

The endpoint returns a JSON object containing the URL to the generated 3D Tileset and details about the height recommendation.

*Example:*
```json
{
  "tileset_url": "/static/tilesets/scene_PlotA123_height/tileset.json",
  "height_recommendation": {
    "value": 75.5,
    "plot_id": "PlotA123",
    "position": [123.456, 78.910, 0]
  }
}
```

*   `tileset_url`: The URL path from which the main `tileset.json` file can be accessed. This URL is relative to the server's host.
*   `height_recommendation`: An object containing details for the target plot.
    *   `value`: The recommended building height (float).
    *   `plot_id`: The identifier of the target plot.
    *   `position`: An array `[longitude, latitude, altitude]` representing the centroid of the target plot. Altitude is typically `0` for ground-level placement of a label or marker.
*   If the target plot is not found or a height recommendation cannot be made, `height_recommendation` will be `null`.

**Error Responses:**

*   **404 Not Found:** If required GIS data files (e.g., `buildings_file`, `land_use_file`) are not found at the specified paths or are empty.
*   **500 Internal Server Error:** If any other error occurs during data processing, analysis, or tileset generation. The response detail may contain more information.

## Setup and Running

1.  **Clone the Repository:**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```

2.  **Install Dependencies:**
    Ensure Python 3.8+ is installed. It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install geopandas shapely numpy trimesh pygltflib py3dtiles fastapi "uvicorn[standard]" python-multipart rtree
    ```
    (Alternatively, if a `requirements.txt` is provided: `pip install -r requirements.txt`)

3.  **Prepare Your Data:**
    *   Place your GIS data files (Shapefiles, GeoJSON, etc.) in a directory accessible by the server, typically the `data/` directory within the project root.
    *   **Building Data Requirements:** The building layer must include an attribute (column) specifying the height of each building (e.g., "height").
    *   **Land Use Data Requirements:** If using height recommendation, the land use layer must include an attribute for unique plot identifiers (e.g., "plot_ID").

4.  **Run the API Server:**
    Execute the following command from the **project root directory**:
    ```bash
    python -m skyline_agent.api_server
    ```
    Or, for development with auto-reload:
    ```bash
    uvicorn skyline_agent.api_server:app --reload --host 0.0.0.0 --port 8000
    ```
    The server will typically start on `http://localhost:8000`.

5.  **Accessing the API:**
    *   Open your browser or API client (like Postman or curl) and navigate to an endpoint, e.g.:
        `http://localhost:8000/scene_data/?target_plot_id=MyPlotID&buildings_file=data/my_city_buildings.shp`
    *   Remember that input data paths specified in API calls (e.g., `buildings_file`) are relative to the project root directory where the server is running.

6.  **Output Data:**
    *   Generated 3D Tilesets are stored in the `static/tilesets/` directory within the project root.
    *   These are served statically by the API server under the `/static/tilesets/` URL path, as indicated by the `tileset_url` in the API response.

## CesiumJS Frontend Integration (Conceptual Guide)

This outlines how a CesiumJS client application can interact with the Skyline Agent API to visualize 3D urban scenes.

1.  **Make API Request:**
    *   The CesiumJS client constructs a GET request to the `/scene_data/` endpoint of the Skyline Agent API.
    *   Parameters for GIS data files (`buildings_file`, `land_use_file`, etc.) and analysis (`target_plot_id`, `height_column`, etc.) are included as query parameters in the URL.
    *   *Example using JavaScript `fetch` API:*
        ```javascript
        const params = new URLSearchParams({
            buildings_file: 'data/city_buildings.shp',
            land_use_file: 'data/city_landuse.shp',
            height_column: 'BLDG_HEIGHT',
            plot_id_column: 'PARCEL_ID',
            target_plot_id: 'Parcel_XYZ'
        });
        const response = await fetch(`http://localhost:8000/scene_data/?${params.toString()}`);
        const data = await response.json();
        ```

2.  **Parse JSON Response:**
    *   The client receives a JSON response from the API. This response includes:
        *   `tileset_url`: The URL path to the generated `tileset.json`.
        *   `height_recommendation`: An object with the recommended height (`value`), `plot_id`, and `position` (centroid coordinates `[lon, lat, alt]`) for the target plot, or `null`.

3.  **Load 3D Tileset into CesiumJS:**
    *   Using the `tileset_url` from the response, the client creates a `Cesium.Cesium3DTileset` object and adds it to the Cesium viewer's scene.
    *   *Example:*
        ```javascript
        // Assuming 'viewer' is your Cesium.Viewer instance
        // and 'data.tileset_url' is like "/static/tilesets/scene_Parcel_XYZ_BLDG_HEIGHT/tileset.json"
        const tileset = await Cesium.Cesium3DTileset.fromUrl(data.tileset_url);
        viewer.scene.primitives.add(tileset);
        
        // Optionally, zoom to the tileset
        viewer.zoomTo(tileset);
        ```

4.  **Display Height Recommendation (Optional):**
    *   If `data.height_recommendation` is not `null`, the client can use its `value` and `position` to display this information in the 3D scene.
    *   This could be a text label, a billboard, or a custom HTML element positioned at the target plot's centroid.
    *   *Example using Cesium.LabelGraphics:*
        ```javascript
        if (data.height_recommendation) {
            const rec = data.height_recommendation;
            const position = Cesium.Cartesian3.fromDegrees(rec.position[0], rec.position[1], rec.position[2]);
            viewer.entities.add({
                position: position,
                label: {
                    text: `Recommended Height: ${rec.value.toFixed(1)}m`,
                    font: '14pt sans-serif',
                    fillColor: Cesium.Color.YELLOW,
                    outlineColor: Cesium.Color.BLACK,
                    outlineWidth: 2,
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -9) // Offset label above the point
                }
            });
        }
        ```

This integration allows for dynamic generation and visualization of 3D city models based on user-selected datasets and parameters, along with analytical overlays like building height recommendations.
(Note: The original "3D Tiles Generation Pipeline (Planned)" section has been effectively integrated or superseded by the API documentation and the new architecture description.)

## Manual Testing and Verification

This section describes the steps to manually test the entire Skyline Agent system, from running the server to visualizing the output in CesiumJS.

### 1. Prerequisites

*   **Dependencies:** Ensure all Python dependencies listed in the "Required Dependencies" section are installed.
*   **Sample GIS Data:**
    *   Prepare sample GIS data files. You'll need:
        *   A buildings layer (e.g., Shapefile, GeoJSON) with a height attribute.
        *   A land use layer (e.g., Shapefile, GeoJSON) with a unique plot ID attribute.
    *   Place these files in a directory accessible by the server, for example, a `data/` directory in the project root.

### 2. Run the API Server

*   Navigate to the project root directory in your terminal.
*   Start the FastAPI server using one of the following commands:
    *   For standard execution:
        ```bash
        python -m skyline_agent.api_server
        ```
    *   For development with auto-reload:
        ```bash
        uvicorn skyline_agent.api_server:app --reload --host 0.0.0.0 --port 8000
        ```
    *   The server should start, typically listening on `http://localhost:8000`.

### 3. Send API Request

*   You can send a GET request to the `/scene_data/` endpoint using `curl` in your terminal or by pasting the URL into a web browser.
*   **Example Request URL:**
    ```
    http://localhost:8000/scene_data/?buildings_file=data/your_buildings.shp&land_use_file=data/your_landuse.shp&height_column=YourHeightCol&plot_id_column=YourPlotIDCol&target_plot_id=SomePlotID
    ```
*   **Important:** Replace `data/your_buildings.shp`, `data/your_landuse.shp`, `YourHeightCol`, `YourPlotIDCol`, and `SomePlotID` with the actual paths (relative to the project root) and names corresponding to your data.

### 4. Inspect API Response & Server Output

*   **API Response:**
    *   If successful, the browser or `curl` output will show a JSON response like:
        ```json
        {
          "tileset_url": "/static/tilesets/scene_SomePlotID_YourHeightCol/tileset.json",
          "height_recommendation": {
            "value": 25.7, // Example value
            "plot_id": "SomePlotID",
            "position": [123.45, 67.89, 0] // Example coordinates
          }
        }
        ```
    *   Note the `tileset_url` and the `height_recommendation` details.
*   **Server Console Logs:**
    *   Check the terminal window where you started the API server. It will show logs detailing the request processing, data loading, analysis steps, tileset generation, and any errors encountered.
*   **Verify Tileset Creation:**
    *   Navigate to the `static/tilesets/` directory within your project.
    *   You should find a subdirectory named according to your request parameters (e.g., `scene_SomePlotID_YourHeightCol`).
    *   Inside this subdirectory, verify that `tileset.json` and a `tiles` folder (containing `.b3dm` files) have been created.

### 5. Basic CesiumJS Visualization Test

*   **Create an HTML file:** Create a new file named `cesium_test.html` (or similar) with the following content:
    ```html
    <!DOCTYPE html>
    <html>
    <head>
      <title>Cesium 3D Tiles Test</title>
      <script src="https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/Cesium.js"></script>
      <link href="https://cesium.com/downloads/cesiumjs/releases/1.118/Build/Cesium/Widgets/widgets.css" rel="stylesheet">
      <style> html, body, #cesiumContainer { width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; } </style>
    </head>
    <body>
      <div id="cesiumContainer"></div>
      <script>
        // Optional: Set your Cesium Ion access token if you want to use Cesium Ion assets like global terrain or imagery.
        // Cesium.Ion.defaultAccessToken = 'YOUR_CESIUM_ION_ACCESS_TOKEN';

        const viewer = new Cesium.Viewer('cesiumContainer', {
          // Use a default imagery provider if not using Cesium Ion
          // imageryProvider: new Cesium.TileMapServiceImageryProvider({
          //   url: Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"),
          // }),
          // terrainProvider: new Cesium.EllipsoidTerrainProvider(), // Basic terrain
        });

        // IMPORTANT: Replace with the actual tileset_url from the API response
        const tilesetUrlFromApi = 'http://localhost:8000/static/tilesets/YOUR_SCENE_ID_FROM_API_RESPONSE/tileset.json'; 

        async function loadTileset() {
          try {
            const tileset = await Cesium.Cesium3DTileset.fromUrl(tilesetUrlFromApi);
            viewer.scene.primitives.add(tileset);
            await viewer.zoomTo(tileset);
          } catch (error) {
            console.error(`Error loading tileset: ${error}`);
            alert(`Failed to load tileset. Check console for details. URL: ${tilesetUrlFromApi}`);
          }
        }

        loadTileset();
      </script>
    </body>
    </html>
    ```
*   **Modify the HTML file:**
    *   **`YOUR_CESIUM_ION_ACCESS_TOKEN`**: If you have a Cesium Ion account and want to use its base layers (terrain, imagery), replace this with your actual token. Otherwise, you can comment out or remove this line and optionally use basic imagery/terrain providers as shown in the commented-out `Viewer` options.
    *   **`tilesetUrlFromApi`**: **Crucially**, replace `'http://localhost:8000/static/tilesets/YOUR_SCENE_ID_FROM_API_RESPONSE/tileset.json'` with the actual `tileset_url` value you received from the API response (e.g., `http://localhost:8000/static/tilesets/scene_SomePlotID_YourHeightCol/tileset.json`).
*   **Open in Browser:** Save the HTML file and open it in a modern web browser (like Chrome, Firefox, Edge).
*   **Verification:**
    *   The CesiumJS viewer should load.
    *   After a short period, your 3D building models should appear in the scene.
    *   You should be able to navigate (pan, zoom, rotate) the 3D scene.
    *   Check the browser's developer console (usually by pressing F12) for any error messages, especially if the tileset doesn't load. Common issues might be incorrect URL, server not running, or CORS problems if accessing from a different domain (though `localhost` to `localhost` should be fine).

### 6. Verify Recommendation (Conceptual)

*   The basic CesiumJS test above does not automatically display the height recommendation text.
*   To visualize the `height_recommendation` (e.g., as a text label on the target plot):
    1.  Your CesiumJS client would need to parse the `height_recommendation` object from the API's JSON response.
    2.  If the recommendation is present, extract the `value` and `position` (`[longitude, latitude, altitude]`).
    3.  Use CesiumJS APIs (e.g., `viewer.entities.add` with `Cesium.LabelGraphics`) to create a label entity at the specified `position`.
    *   Refer to the "CesiumJS Frontend Integration (Conceptual Guide)" section for an example code snippet on how to add a label.