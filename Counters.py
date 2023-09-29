#Import librairies
import pandas as pd
import numpy as np
import geopandas as gpd
import json
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster, MousePosition
from folium.features import GeoJson


#Import files
#bike counter data
url_bike = 'https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/comptage-velo-donnees-compteurs/exports/csv?lang=fr&timezone=Europe%2FParis&use_labels=true&delimiter=%3B'
df = pd.read_csv(url_bike, sep=';')
#Districts data in Paris 
url_districts = https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/arrondissements/exports/geojson?lang=fr&timezone=Europe%2FBerlin
districts = gpd.read_file('url')


#df: working on colonnes
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

#Creatie "Longitude" and "Lagititude" columns from the 'Coords' column and remove 'Coords' column
df['Longitude'] = df['Coords'].apply(lambda x: x.split(',')[0]).astype(float)
df['Latitude'] = df['Coords'].apply(lambda x: x.split(',')[1]).astype(float)
df = df.drop(columns='Coords')

#Remove some extreme values (outliers) due to counter dysfunction (found during exploratory data analysis)
df = df[df['Count']<2000]

#Working on districts data by removing some columns and and renaming retained columns
districts = districts.drop(columns = ['n_sq_co', 'l_aroff', 'c_arinsee', 'n_sq_ar'])
districts = districts.rename(columns={'c_ar': 'District', 'l_ar':'District_name', 'surface':'Surface', 'perimetre': 'Perimeter'})

#Create a new 'Coords' column from df['Longitude'], df['Latitude'] and set it as geometry column for GeoDataframe
df['Coords'] = list(zip(df['Latitude'], df['Longitude']))
df['Coords'] = df['Coords'].apply(Point)

# Convert df to a GeoDataframe by setting  geometry column as 'Coords'
df_geo = gpd.GeoDataFrame(df, geometry='Coords', crs=districts.crs)
# Joint df_geo with districts by using spatial joint tool provided by GeoPandas
df_geo = gpd.tools.sjoin(df_geo, districts, how='inner', op='intersects', lsuffix ='Coords', rsuffix = 'geometry')

#Remove some columns that will not be necessary for our purpose
df_geo = df_geo.drop(columns = ['Surface', 'Perimeter', 'index_geometry'])
#df_Paris_geo.to_csv('df_Paris_geo.csv', sep=',', index=False, float_format='%g')

#Create the base map
paris_m = folium.Map(location=[48.856578, 2.351828], 
                    zoom_start=12, min_zoom=10, max_zoom=15, 
                    control_scale=True) #Show a scale on the bottom of the map.

#create a featuregroup including chroropleth and marker maps subgroups
fg = folium.FeatureGroup(name="Counters and hourly count average")
paris_m.add_child(fg)
circle_fg = folium.plugins.FeatureGroupSubGroup(fg, "Average hourly count")#, show=False)
paris_m.add_child(circle_fg)
marker_fg = folium.plugins.FeatureGroupSubGroup(fg, "Counter address")#, show=False)
paris_m.add_child(marker_fg)

dist_mean = df_geo.groupby(["District"], as_index = False)['Count'].mean()
dist_mean = pd.DataFrame({"District" : dist_mean["District"],
                          "Count" : round(dist_mean["Count"])})

# Create the choropleth map and add it to a FeatureGroup
choropleth = folium.Choropleth(
    geo_data=districts,
    key_on="feature.properties.District",
    data=dist_mean,
    columns=["District", "Count"],
    tooltip=f'District: {"District"}', 
    popup='District',
    fill_color="BuPu",  # or any other color scheme
    highlight=True,
    legend_name="Average hourly count by district",
    name="District choropleth"
).add_to(paris_m)
# Create the marker and circle marker map and add it to a FeatureGroup

df_address = df_geo.groupby(['Address', 'Longitude', 'Latitude'], as_index=False)['Count'].mean()

for index, row in df_address.iterrows():
    size = row['Count'] / 10  #Get circle size proportional to hourly count
    count_data = round(row['Count'])
    counter_address = row['Address']
    circle = folium.CircleMarker([row['Longitude'], row['Latitude']], 
                                radius=size, 
                                tooltip=f'Average hourly count: {count_data}', 
                                popup=f'Counter address: {counter_address}', 
                                fill=True, fill_color='purple', fill_opacity=0.7, 
                                highlight=True,).add_to(circle_fg)
    marker = folium.Marker(location=[row['Longitude'], row['Latitude']], 
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
