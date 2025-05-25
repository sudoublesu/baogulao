import pyvista as pv
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString

def setup_plotter() -> pv.Plotter:
    """
    Creates and returns a PyVista Plotter object.

    Returns:
        pv.Plotter: A PyVista Plotter object.
    """
    plotter = pv.Plotter()
    plotter.set_background('lightgrey')
    return plotter

def add_buildings_to_plotter(plotter: pv.Plotter, buildings_gdf: gpd.GeoDataFrame, height_column: str, color: str = 'tan', opacity: float = 1.0):
    """
    Adds building meshes to a PyVista Plotter.

    Args:
        plotter: The PyVista Plotter to add the buildings to.
        buildings_gdf: GeoDataFrame containing building polygons.
        height_column: Name of the column in buildings_gdf with height values.
        color: Color of the building meshes.
        opacity: Opacity of the building meshes.
    """
    for index, building in buildings_gdf.iterrows():
        geom = building.geometry
        try:
            height = float(building[height_column])
            if height <= 0:
                print(f"Warning: Building at index {index} has non-positive height ({height}). Skipping.")
                continue
        except (ValueError, TypeError, KeyError) as e:
            print(f"Warning: Could not get valid height for building at index {index} from column '{height_column}'. Error: {e}. Skipping.")
            continue

        if geom.geom_type == 'Polygon':
            # Ensure polygon is 2D (z=0) for extrusion
            exterior_coords = [(x, y, 0) for x, y, *z in list(geom.exterior.coords)]
            if len(exterior_coords) < 3:
                print(f"Warning: Building polygon at index {index} has less than 3 points. Skipping.")
                continue
            try:
                # Create PyVista polygon and extrude
                pv_polygon = pv.Polygon(exterior_coords)
                mesh = pv_polygon.extrude((0, 0, height), capping=True)
                plotter.add_mesh(mesh, color=color, opacity=opacity, show_edges=True, edge_color='black', line_width=0.5)
            except Exception as e:
                print(f"Error processing building at index {index}: {e}")
        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                exterior_coords = [(x, y, 0) for x, y, *z in list(poly.exterior.coords)]
                if len(exterior_coords) < 3:
                    print(f"Warning: Building sub-polygon at index {index} has less than 3 points. Skipping.")
                    continue
                try:
                    pv_polygon = pv.Polygon(exterior_coords)
                    mesh = pv_polygon.extrude((0, 0, height), capping=True)
                    plotter.add_mesh(mesh, color=color, opacity=opacity, show_edges=True, edge_color='black', line_width=0.5)
                except Exception as e:
                    print(f"Error processing building sub-polygon at index {index}: {e}")
        else:
            print(f"Warning: Building at index {index} has unhandled geometry type {geom.geom_type}. Skipping.")


def add_geodataframe_to_plotter(plotter: pv.Plotter, gdf: gpd.GeoDataFrame, color: str = 'blue', line_width: int = 1, opacity: float = 0.7):
    """
    Adds GeoDataFrame geometries (Polygons, LineStrings) to a PyVista Plotter.

    Args:
        plotter: The PyVista Plotter to add the geometries to.
        gdf: GeoDataFrame containing the geometries.
        color: Color of the meshes/lines.
        line_width: Line width for LineString geometries.
        opacity: Opacity of the meshes/lines.
    """
    for index, feature in gdf.iterrows():
        geom = feature.geometry
        
        if geom is None or geom.is_empty:
            print(f"Warning: Empty geometry at index {index}. Skipping.")
            continue

        if geom.geom_type == 'Polygon':
            exterior_coords = list(geom.exterior.coords)
            # Ensure polygon is 2D (z=0)
            points = [(x, y, 0) for x, y, *z in exterior_coords]
            if len(points) < 3:
                print(f"Warning: Polygon at index {index} has less than 3 points. Skipping.")
                continue
            try:
                mesh = pv.PolyData(points) # pv.Polygon creates a filled polygon face
                # To make it a flat mesh on the ground, we can create a surface from points
                # or if it's meant to be a filled polygon, pv.Polygon might be better
                # For land use, a flat representation is usually desired.
                # We need to create faces for PolyData to make it a surface
                if len(points) >=3:
                    faces = [len(points)] + list(range(len(points)))
                    mesh = pv.PolyData([points], faces=faces)
                    plotter.add_mesh(mesh, color=color, opacity=opacity, show_edges=True, edge_color='grey', line_width=0.2)
            except Exception as e:
                print(f"Error processing Polygon at index {index}: {e}")

        elif geom.geom_type == 'MultiPolygon':
            for poly in geom.geoms:
                exterior_coords = list(poly.exterior.coords)
                points = [(x, y, 0) for x, y, *z in exterior_coords]
                if len(points) < 3:
                    print(f"Warning: Sub-Polygon at index {index} has less than 3 points. Skipping.")
                    continue
                try:
                    if len(points) >=3:
                        faces = [len(points)] + list(range(len(points)))
                        mesh = pv.PolyData([points], faces=faces)
                        plotter.add_mesh(mesh, color=color, opacity=opacity, show_edges=True, edge_color='grey', line_width=0.2)
                except Exception as e:
                    print(f"Error processing MultiPolygon sub-geometry at index {index}: {e}")

        elif geom.geom_type == 'LineString':
            points = [(x, y, 0) for x, y, *z in list(geom.coords)]
            if len(points) < 2:
                print(f"Warning: LineString at index {index} has less than 2 points. Skipping.")
                continue
            try:
                line_mesh = pv.lines_from_points(points, close=False)
                plotter.add_mesh(line_mesh, color=color, line_width=line_width, opacity=opacity)
            except Exception as e:
                print(f"Error processing LineString at index {index}: {e}")

        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                points = [(x, y, 0) for x, y, *z in list(line.coords)]
                if len(points) < 2:
                    print(f"Warning: Sub-LineString at index {index} has less than 2 points. Skipping.")
                    continue
                try:
                    line_mesh = pv.lines_from_points(points, close=False)
                    plotter.add_mesh(line_mesh, color=color, line_width=line_width, opacity=opacity)
                except Exception as e:
                    print(f"Error processing MultiLineString sub-geometry at index {index}: {e}")
        else:
            print(f"Warning: Feature at index {index} has unhandled geometry type {geom.geom_type}. Skipping.")

def add_height_labels_to_plotter(plotter: pv.Plotter, buildings_gdf: gpd.GeoDataFrame, height_column: str, font_size: int = 10, text_color: str = 'black'):
    """
    Adds height labels for buildings to a PyVista Plotter.

    Args:
        plotter: The PyVista Plotter to add the labels to.
        buildings_gdf: GeoDataFrame containing building polygons.
        height_column: Name of the column in buildings_gdf with height values.
        font_size: Font size for the labels.
        text_color: Color of the label text.
    """
    for index, building in buildings_gdf.iterrows():
        geom = building.geometry
        try:
            height = float(building[height_column])
            if height <= 0:
                # print(f"Warning: Building at index {index} has non-positive height ({height}) for label. Skipping.")
                continue # Skip label if height is not positive
        except (ValueError, TypeError, KeyError) as e:
            print(f"Warning: Could not get valid height for label at building index {index} from column '{height_column}'. Error: {e}. Skipping.")
            continue

        if geom is None or geom.is_empty:
            print(f"Warning: Empty geometry for building at index {index}. Cannot add label. Skipping.")
            continue

        try:
            centroid = geom.centroid
            if centroid is None or centroid.is_empty:
                print(f"Warning: Could not calculate centroid for building at index {index}. Cannot add label. Skipping.")
                continue
            
            # Position label slightly above the building height at its centroid
            label_position = (centroid.x, centroid.y, height + height * 0.1) # 10% above height
            label_text = f"{height:.1f}m" # Format height to one decimal place

            plotter.add_point_labels(
                points=[label_position], 
                labels=[label_text], 
                font_size=font_size, 
                text_color=text_color,
                shape_opacity=0, # Make the point itself invisible
                show_points=False
            )
        except Exception as e:
            print(f"Error adding label for building at index {index}: {e}")
