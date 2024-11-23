import folium
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, LineString

class DataProcessor:
    def __init__(self, seismic_path = None, fault_path = None):
        self.seismic_path = seismic_path
        self.fault_path = fault_path

    def _load_gpd_files(self):
        geo_df_seismic = gpd.read_file(self.seismic_path)
        geo_df_faults = gpd.read_file(self.fault_path)
        if geo_df_seismic.crs != 'EPSG:4326':
            geo_df_seismic = geo_df_seismic.to_crs('EPSG:4326')
        if geo_df_faults.crs != 'EPSG:4326':
            geo_df_faults = geo_df_faults.to_crs('EPSG:4326')

        return geo_df_seismic, geo_df_faults

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
        
        def calculate_min_distance_vectorized(building_geom, fault_lines_gdf):
            # Compute distances to all fault lines
            distances = fault_lines_gdf.distance(building_geom)
            # Apply the function to each distance
            values = np.minimum(distances**2, 100)
            # Find the minimum value
            return values.min()

        buildings_gdf['min_distance_value'] = buildings_gdf.geometry.apply(calculate_min_distance_vectorized)

        return buildings_gdf