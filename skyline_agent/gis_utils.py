import geopandas as gpd

def load_buildings(file_path: str) -> gpd.GeoDataFrame:
    """
    Loads building data from a file.

    Args:
        file_path: The path to the file containing building data.

    Returns:
        A GeoDataFrame containing the building data.
    """
    try:
        buildings = gpd.read_file(file_path)
        return buildings
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return gpd.GeoDataFrame()
    except Exception as e:
        print(f"Error loading building data from {file_path}: {e}")
        return gpd.GeoDataFrame()

def load_roads(file_path: str) -> gpd.GeoDataFrame:
    """
    Loads road data from a file.

    Args:
        file_path: The path to the file containing road data.

    Returns:
        A GeoDataFrame containing the road data.
    """
    try:
        roads = gpd.read_file(file_path)
        return roads
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return gpd.GeoDataFrame()
    except Exception as e:
        print(f"Error loading road data from {file_path}: {e}")
        return gpd.GeoDataFrame()

def load_land_use(file_path: str) -> gpd.GeoDataFrame:
    """
    Loads land use data from a file.

    Args:
        file_path: The path to the file containing land use data.

    Returns:
        A GeoDataFrame containing the land use data.
    """
    try:
        land_use = gpd.read_file(file_path)
        return land_use
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return gpd.GeoDataFrame()
    except Exception as e:
        print(f"Error loading land use data from {file_path}: {e}")
        return gpd.GeoDataFrame()
