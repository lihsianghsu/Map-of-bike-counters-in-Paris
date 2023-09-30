#Import libraries
import pandas as pd
import geopandas as gpd
import json
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster, MousePosition
from folium.features import GeoJson

#Import files
#bike counter data
df = pd.read_csv('comptage-velo-donnees-compteurs.csv', sep=';')
#District data in Paris 
districts = gpd.read_file('arrondissements.geojson')

#Alternally, import files directly from the site of Paris Open Data
#bike counter data
#url_bike = 'https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/comptage-velo-donnees-compteurs/exports/csv?lang=fr&timezone=Europe%2FParis&use_labels=true&delimiter=%3B'
#df = pd.read_csv(url_bike, sep=';')
#district data 
#url_districts = 'https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/arrondissements/exports/geojson?lang=fr&timezone=Europe%2FBerlin'
#districts = gpd.read_file(url_districts)

#Working on bike counter data (df) colonnes
df.columns = df.columns.astype(str).str.replace(" ", "_")

df = df.drop(columns = ['Identifiant_du_compteur', 
                        'Identifiant_du_site_de_comptage',
                        'Nom_du_site_de_comptage',
                        "Date_d'installation_du_site_de_comptage",
                        'Lien_vers_photo_du_site_de_comptage',
                        'Identifiant_technique_compteur', 
                        'ID_Photos',
                        'test_lien_vers_photos_du_site_de_comptage_', 
                        'id_photo_1', 
                        'url_sites',
                        'type_dimage',
                        'mois_annee_comptage',
                        'Date_et_heure_de_comptage'])
# Rename columns
df = df.rename(columns={'Nom_du_compteur': 'Address', 
                        'Comptage_horaire': 'Count', 
                        'Coordonnées_géographiques': 'Coords'})

#Working on districts data by removing some columns and and renaming retained columns
districts = districts.drop(columns = ['n_sq_co', 'l_aroff', 'c_arinsee', 'n_sq_ar', 'surface', 'perimetre', 'l_ar'])
districts = districts.rename(columns={'c_ar': 'District'})

#Create "Longitude" and "Lagititude" columns from the 'Coords' column
df['Latitude'] = df['Coords'].apply(lambda x: x.split(',')[0]).astype(float)
df['Longitude'] = df['Coords'].apply(lambda x: x.split(',')[1]).astype(float)
#Remove 'Coords' column
df = df.drop(columns='Coords')

#Create a new 'Coords' column from df['Longitude'], df['Latitude'] and set it as geometry column for GeoDataframe
df['Coords'] = gpd.points_from_xy(df.Longitude, df.Latitude)

#Another methode to create the 'Coords' column
#df['Coords'] = list(zip(df['Longitude'], df['Latitude']))
#df['Coords'] = df['Coords'].apply(Point)

# Convert df to GeoDataframe by setting 'Coords' column as geometry
df_geo = gpd.GeoDataFrame(df, geometry='Coords', crs=districts.crs)

# Joint df_geo with districts by using spatial joint tool provided by GeoPandas
df_geo = gpd.tools.sjoin(df_geo, districts, how='inner', op='intersects', lsuffix ='Coords', rsuffix = 'geometry')

#Create the base map
paris_m = folium.Map(location=[48.856578, 2.351828], 
                    zoom_start=12, min_zoom=10, max_zoom=15, 
                    control_scale=True) #Show a scale on the bottom of the map.

#Compute the mean hourly count for every district in Paris
dist_mean = df_geo.groupby("District", as_index = False)["Count"].mean()

# Create the choropleth map and add it to the base map
choropleth = folium.Choropleth(geo_data=districts,
                              key_on="feature.properties.District",
                              data=dist_mean,
                              columns=["District", "Count"],
                              fill_color="BuPu",  # or any other color scheme
                              highlight=True,
                              legend_name="Average hourly count by district",
                              name="District choropleth").add_to(paris_m)

#create a featuregroup including circle and marker subgroups
fg = folium.FeatureGroup(name="Counters and hourly count average")
paris_m.add_child(fg)
circle_fg = folium.plugins.FeatureGroupSubGroup(fg, "Average hourly count", show=False)
paris_m.add_child(circle_fg)
marker_fg = folium.plugins.FeatureGroupSubGroup(fg, "Counter address", show=False)
paris_m.add_child(marker_fg)

#Get the mean hourly count for every counter
df_address = df_geo.groupby(['Address', 'Longitude', 'Latitude'], as_index=False)['Count'].mean()

# Create a marker and circle marker map and add it to a FeatureGroup
for index, row in df_address.iterrows():
    size = row['Count'] / 10  #Get circle size proportional to hourly count
    count_data = round(row['Count'])
    counter_address = row['Address']
    circle = folium.CircleMarker([row['Latitude'], row['Longitude']], 
                                radius=size, 
                                tooltip=f'Average hourly count: {count_data}', 
                                popup=f'Counter address: {counter_address}', 
                                fill=True, fill_color='purple', fill_opacity=0.7, 
                                highlight=True,).add_to(circle_fg)
    marker = folium.Marker(location=[row['Latitude'], row['Longitude']], 
                        color='blue', 
                        tooltip=f'Counter address: {counter_address}', 
                        popup=f'Average hourly count: {count_data}',
                        icon=folium.Icon(color="darkblue"),
                        highlight=True).add_to(marker_fg)

# Add Layer Control to the map to toggle between Choropleth and Markers and Circles
folium.LayerControl(collapsed=False, autoZIndex=True).add_to(paris_m)

# Save the map to show in a webbrowser
paris_m.save('paris_map.html')  

# Display the map
paris_m
