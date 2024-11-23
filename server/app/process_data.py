import folium
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, LineString
from shapely.ops import nearest_points
from geopy.distance import geodesic
from math import sqrt

class DataProcessor:
    def __init__(self, seismic_path = None, fault_path = None, buildings_path = None):
        self.seismic_path = seismic_path
        self.fault_path = fault_path
        self.projected_crs = 'EPSG:4326'
        self.buildings_path = buildings_path

    def _load_gpd_files(self):
        geo_df_seismic = gpd.read_file(self.seismic_path)
        geo_df_faults = gpd.read_file(self.fault_path)
        if geo_df_seismic.crs != self.projected_crs:
            geo_df_seismic = geo_df_seismic.to_crs(self.projected_crs)
        if geo_df_faults.crs != self.projected_crs:
            geo_df_faults = geo_df_faults.to_crs(self.projected_crs)

        return geo_df_seismic, geo_df_faults
    
    def _load_buildings_file(self):
        buildings_gdf_simplified = gpd.read_file(self.buildings_path)
        if buildings_gdf_simplified.crs != self.projected_crs:
            buildings_gdf_simplified = buildings_gdf_simplified.to_crs(self.projected_crs)
        return buildings_gdf_simplified

    def create_seismic_fault_plot(self):
        geo_df_seismic, geo_df_faults = self._load_gpd_files()

        # Calculate the mean coordinates to center the map
        mean_lat = geo_df_seismic.geometry.centroid.y.mean()
        mean_lon = geo_df_seismic.geometry.centroid.x.mean()

        # Create the map
        m = folium.Map(location=[mean_lat, mean_lon], zoom_start=10)

        # Function to style the geometries
        def style_function(feature):
            return {
                'fillColor': '#228B22',  # Fill color (e.g., Forest Green)
                'color': 'black',        # Outline color
                'weight': 1,             # Outline width
                'fillOpacity': 0.6,      # Fill opacity
            }


        # Function to create popups
        def popup_function(feature):
            return folium.Popup(feature['properties']['id'])  # Replace 'name' with a column from your GeoDataFrame

        # Add GeoJson layer with style and popup
        folium.GeoJson(
            geo_df_seismic,
            name='GeoData',
            style_function=style_function,
            tooltip=folium.features.GeoJsonTooltip(fields=['id']),  # Replace 'name' with actual column(s)
            popup=folium.features.GeoJsonPopup(fields=['id']),
        ).add_to(m)

        # Add GeoJson layer with style and popup
        folium.GeoJson(
            geo_df_faults,
            name='GeoData',
            style_function=style_function,
            tooltip=folium.features.GeoJsonTooltip(fields=['id']),  # Replace 'name' with actual column(s)
            popup=folium.features.GeoJsonPopup(fields=['id']),
        ).add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)
        return m._repr_html_()

    def extract_polygons(self):

        geo_df_seismic, geo_df_faults = self._load_gpd_files()

        seismic_polygons = geo_df_seismic.geometry
        fault_lines = geo_df_faults.geometry

        return seismic_polygons, fault_lines
    
    def fault_processing(self, buildings_gdf):
        '''
        f (min(min(di^2), 100)) - output - single coefficient (0-1) from the closest fault
        '''
        _, fault_lines_gdf = self._load_gpd_files()
        
        def calculate_min_geodesic_distance(building_geom):
            # Get possible fault lines near the building
            fault_sindex = fault_lines_gdf.sindex
            possible_faults_index = list(fault_sindex.intersection(building_geom.bounds))
            possible_faults = fault_lines_gdf.iloc[possible_faults_index]
            
            min_value = np.inf  # Initialize minimum value
            
            for fault_geom in possible_faults.geometry:
                # Find the nearest points between building and fault line
                nearest_points_pair = nearest_points(building_geom, fault_geom)
                
                # Extract coordinate pairs
                coord_building = (nearest_points_pair[0].y, nearest_points_pair[0].x)
                coord_fault = (nearest_points_pair[1].y, nearest_points_pair[1].x)
                
                # Calculate geodesic distance in meters
                distance = geodesic(coord_building, coord_fault).meters
                
                # Apply the function min(distance^2, 100)
                value = min(distance**2, 10000)
                
                if value < min_value:
                    min_value = value
            
            # Handle case where no fault lines are nearby
            if min_value == np.inf:
                return 100  # or some default value
            else:
                return sqrt(min_value)

        buildings_gdf['min_distance_value'] = buildings_gdf.geometry.apply(calculate_min_geodesic_distance)

        return buildings_gdf
    
    def get_buildings_with_distance_coeff(self):
        buildings_gdf_simplified = self._load_buildings_file()
        buildings_gdf_simplified = self.fault_processing(self, buildings_gdf_simplified)
        buildings_gdf_simplified['distance_coeff'] = ((100 - buildings_gdf_simplified['min_distance_value']) / 100)**2

        return buildings_gdf_simplified