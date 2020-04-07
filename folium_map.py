# pip install folium
# pip install lightgbm
import pandas as pd
import numpy as np
import branca
import matplotlib.pyplot as plt
from scipy.interpolate import griddata 
import geojsoncontour
import scipy as sp
import scipy.ndimage
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from folium import plugins
import math
from sklearn.model_selection import KFold
from matplotlib import rcParams
import datetime
from datetime import datetime as dt
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from row1_functions import filter_dataframe

print("folium_map.py")
raw_station_data = pd.read_csv("station.csv")
# raw_trip_data = pd.read_csv("trip.csv")
raw_trip_data = pd.read_csv('less_trips.csv')
status_apr = pd.read_csv("SF_status_apr15.csv")
merged = pd.read_csv('merged.csv')
merged["start_date"] = pd.to_datetime(merged["start_date"])
merged["end_date"] = pd.to_datetime(merged["end_date"])
# city filter
unique_city = raw_station_data['city'].unique().tolist()
unique_city.append('All')

now = dt.now()
new_date = now - relativedelta(years=5) # if we change current time to 6 years ago

# def trip_city_merge(raw_trip_data, raw_station_data):
#     #remove duration outliers
#     raw_trip_data['duration_in_minutes'] = raw_trip_data['duration'].apply(lambda x:int(x/60))
#     raw_trip_data = raw_trip_data[raw_trip_data['duration_in_minutes']<5000].reset_index().drop('index',axis=1)
    
#     #remove round trips
#     raw_trip_data = raw_trip_data[raw_trip_data['start_station_id']!=raw_trip_data['end_station_id']]
#     trip_data = raw_trip_data    
    
#     #Create maps for station to long lat 
#     start_station_info = raw_station_data[["id","lat","long"]]
#     start_station_info.columns = ["start_station_id","start_lat","start_long"]


#     end_station_info = raw_station_data[["id","lat","long"]]
#     end_station_info.columns = ["end_station_id","end_lat","end_long"]
    
#     ## merge to get long lat for start and end stations
#     trips_df = trip_data.merge(start_station_info,on="start_station_id")
#     trips_df = trips_df.merge(end_station_info,on="end_station_id")
#     # print(trips_df.info())
#     trips_df['start_date'] = pd.to_datetime(trips_df['start_date'])
#     trips_df['end_date'] = pd.to_datetime(trips_df['end_date'])
# #     return trips_df

# merged = trip_city_merge(raw_trip_data, raw_station_data)
# merged.to_csv('merged.csv')

# function to plot map
def plotgeneralMap(city, station, direction):
    coordinates_plot = [37.575, -122.1]
    zoom_plot = 10
    
    dark_colors = ["#99D699", "#B2B2B2",
                    (0.8509803921568627, 0.37254901960784315, 0.00784313725490196),
                    (0.4588235294117647, 0.4392156862745098, 0.7019607843137254),
                    (0.9058823529411765, 0.1607843137254902, 0.5411764705882353),
                    (0.4, 0.6509803921568628, 0.11764705882352941),
                    (0.9019607843137255, 0.6705882352941176, 0.00784313725490196),
                    (0.6509803921568628, 0.4627450980392157, 0.11372549019607843),
                    (0.4, 0.4, 0.4)]
    rcParams['figure.figsize'] = (24, 18)
    rcParams['figure.dpi'] = 150
    rcParams['lines.linewidth'] = 2
    rcParams['axes.facecolor'] = "white"
    rcParams['axes.titlesize'] = 20      
    rcParams['axes.labelsize'] = 17.5
    rcParams['xtick.labelsize'] = 15 
    rcParams['ytick.labelsize'] = 15
    rcParams['legend.fontsize'] = 17.5
    rcParams['patch.edgecolor'] = 'none'
    rcParams['grid.color']="white"   
    rcParams['grid.linestyle']="-" 
    rcParams['grid.linewidth'] = 1
    rcParams['grid.alpha']=1
    rcParams['text.color'] = "444444"
    rcParams['axes.labelcolor'] = "444444"
    rcParams['ytick.color'] = "444444"
    rcParams['xtick.color'] = "444444"
    
    #####
    ###inflow_outflow = Dictionary for inflow-outflow for each station###
    ###plot_dict = Dictionary for usage across 2 stations###
    plot_dict = dict()
    inflow_outflow = {}

    if (direction == "both"):
        data = filter_dataframe(merged, city, station, new_date, twoway=True)
    elif (direction == "start"):
        data = filter_dataframe(merged, city, station, new_date, start=True)
    else:
        data = filter_dataframe(merged, city, station, new_date, start=False)
    
    for index,row in data.iterrows():
        start_lat = row['start_lat']
        start_long = row['start_long']
        end_lat = row['end_lat']
        end_long = row['end_long']

        key1 = str(start_lat)+'_'+str(start_long)+'_'+str(end_lat)+'_'+str(end_long)

        key2 = row['start_station_id']
        key3 = row['end_station_id']

        if key1 in plot_dict:
            plot_dict[key1] += 1
        else:
            plot_dict[key1] = 1

    ##bikes come in // end of trip        
        if key3 in inflow_outflow:
            inflow_outflow[key3] +=1
        else:
            inflow_outflow[key3] =1

    ##bikes go out // start of trip  
        if key2 in inflow_outflow:
            inflow_outflow[key2] -=1
        else:
            inflow_outflow[key2] =-1
            
    #################################  
    
    ###inflow-outflow for each station into DF###
    flow_id =[]
    flow_amt =[]
    for key,value in inflow_outflow.items():
        flow_id.append(int(key))
        flow_amt.append(int(value))
        
    flow = pd.DataFrame({"id":flow_id,"flow_amt":flow_amt})
    
    ###inflow-outflow for each station DF + longlat
    id_to_longlat = raw_station_data[['id','name','lat','long','city']]
    flow_fullV1 = pd.merge(flow, id_to_longlat, on='id', how='outer')
    
    
    ###percentile calculations for color
    #break into pos & neg percentile
    pos_flow_list = flow[flow.flow_amt > 0]['flow_amt'].tolist()

    pos_flow_list_25 = np.percentile(pos_flow_list, 25)
    pos_flow_list_50 = np.percentile(pos_flow_list, 50)
    pos_flow_list_75 = np.percentile(pos_flow_list, 75)

    neg_flow_list = flow[flow.flow_amt < 0]['flow_amt'].tolist()

    neg_flow_list_M100 = np.percentile(neg_flow_list, 0)
    neg_flow_list_M75 = np.percentile(neg_flow_list, 25)
    neg_flow_list_M50 = np.percentile(neg_flow_list, 50)
    neg_flow_list_M25 = np.percentile(neg_flow_list, 75)
    
    bins = [neg_flow_list_M100-1, neg_flow_list_M75, neg_flow_list_M50, neg_flow_list_M25, 0, pos_flow_list_25, pos_flow_list_50, pos_flow_list_75, math.inf]

    flow_fullV1['flow_amt_binned'] = pd.cut(flow_fullV1['flow_amt'], bins, duplicates='drop')
    flow_fullV1.dropna(inplace=True)
    # print(flow_fullV1.describe())
    listinterv= flow_fullV1.flow_amt_binned.unique().tolist()
    # print("list interv")
    # print(listinterv)

    listinterv_float = []
    for item in listinterv:
        item = str(item)
        item = (item.replace('(','').replace(']','').split(", "))
        item = list(map(float, item))
        listinterv_float.append(item)
    listinterv_float = sorted(listinterv_float)  

    listinterv_char = []
    for item in listinterv_float:
        item = str(item)
        listinterv_char.append(item)
    #listinterv_char is a list of bin range
    
    # count=0
    ###Give each bin a color reference number
    def label_bin (row):
        # print(row)
        st = str(row['flow_amt_binned'])
        st = (st.replace('(','[')) # a list now
        return listinterv_char.index(st)
    
    flow_fullV1['color_number'] = flow_fullV1.apply (lambda row: label_bin(row), axis=1)
    
    ###Plotting General flow undirected edges (usage across 2 stations)
    #Create dataframe for flow
    start_lat = []
    start_long = []
    end_lat = []
    end_long = []
    nb_trips = []
    for key,value in plot_dict.items():
        start_lat.append(float(key.split('_')[0]))
        start_long.append(float(key.split('_')[1]))
        end_lat.append(float(key.split('_')[2]))
        end_long.append(float(key.split('_')[3]))
        nb_trips.append(int(value))

    temp_df = pd.DataFrame({"start_lat":start_lat,"start_long":start_long,"end_lat":end_lat,"end_long":end_long,"nb_trips":nb_trips})
    
    #auto-scale width of edges on map
    denom = 20
    while (max(temp_df['nb_trips'].tolist())/denom)> 20:
        denom *=20
    
    #Create empty map
    directions_map = folium.Map(location=coordinates_plot, zoom_start=zoom_plot)#tiles='Stamen Toner')
    
    
    #Add undirected edges to empty map
    for index,row in temp_df.iterrows():
        points = []

        p1 = [row['start_lat'],row['start_long']]
        p2 = [row['end_lat'],row['end_long']]

        points.append(tuple([row['start_lat'],row['start_long']]))
        points.append(tuple([row['end_lat'],row['end_long']]))

        folium.PolyLine(points,color='blue',weight= 1).add_to(directions_map)

    ###Plotting stations with (inflow-outflow attribute binned and showed by colors)
    #Allocate colors to be used for bins (for each inflow-outflow of stations)
    colors = [
        'red',
        'blue',
        'gray',
        'darkred',
        'lightred',
        'orange',
        'beige',
        'green',
        'darkgreen',
        'lightgreen',
        'darkblue',
        'lightblue',
        'purple',
        'darkpurple',
        'pink',
        'cadetblue',
        'lightgray',
        'black'
    ]
    
    colormap = {}
    # colormap[0] = 'darkred'
    # colormap[1] = 'lightred'
    # colormap[2] = 'orange'
    # colormap[3] = 'yellow'
    # colormap[4] = 'beige'
    # colormap[5] = 'lightgray'
    # colormap[6] = 'lightgreen'
    # colormap[7] = 'green'
    # colormap[8] = 'darkgreen'
    # colormap[9] = 'darkgreen'
    # colormap[10] = 'darkgreen'

    colormap[0] = 'darkred'
    colormap[1] = 'lightred'
    colormap[2] = 'yellow'
    colormap[3] = 'lightgreen'
    colormap[5] = 'darkgreen'
    colormap[4] = 'green'

    colormap_loc = {}

    colormap_loc[1] = 'cadetblue'
    colormap_loc[2] = 'darkblue'
    colormap_loc[3] = 'yellow'
    colormap_loc[4] = 'gray'
    colormap_loc[5] = 'lightgray'

    #CM2
    CM2={}
    CM2["San Francisco"] = 1
    CM2["San Jose"] = 2
    CM2["Palo Alto"] = 3
    CM2["Mountain View"] = 4
    CM2["Redwood City"] = 5
    
    if (city != "San Francisco"):
        #Add station location markers
        for index,row in raw_station_data.iterrows():        
            pop_up= folium.Popup('Station ' + str(row['id']) + ': ' + row['name'], max_width=150,min_width=150),
            tooltip = row['city'],                    
            folium.Marker([float(row['lat']), float(row['long'])], 
            popup=pop_up,
            tooltip=tooltip,
            icon=folium.Icon(
                color=colormap_loc[CM2[row['city']]],
                icon_color='#lightgreen',
                icon='bicycle', 
                prefix='fa')
            ).add_to(directions_map)

    # if zoomed in into a specific city (SF): I want to see the capacity level instead
    else:
        # get the current capacity level - only at SF
        current_info = status_apr[(status_apr["day"]== new_date.day) & (status_apr["hour"] == new_date.hour) & (status_apr["minute"] == new_date.minute)]
        current_info["name"] = current_info["station_id"].apply(lambda x: raw_station_data[raw_station_data["id"] == int(x)]["name"].values[0])

        for index,row in raw_station_data.iterrows():
            if (len(current_info[current_info["station_id"]==int(row['id'])].values)):
                # get current capacity
                cap_here = (current_info[current_info["station_id"]==int(row['id'])]["capacity"].values[0])
                cap_mod = int(cap_here//20) # changed the scale
                pop_up= folium.Popup('Station ' + str(row['id']) + ': ' + row['name'] + '\n' + ", Capacity: " + str(cap_here) + "%", max_width=150,min_width=150)
                tooltip = row['name']
                if (str(row['name']) == str(station)):
                    folium.Marker([float(row['lat']), float(row['long'])], 
                    popup=pop_up,
                    tooltip=tooltip,
                    icon=folium.Icon(     
                        color=colormap[cap_mod],
                        icon_color='#lightgreen',
                        icon='info', 
                        prefix='fa')
                    ).add_to(directions_map)
                else:    
                    folium.Marker([float(row['lat']), float(row['long'])], 
                    popup=pop_up,
                    tooltip=tooltip,
                    icon=folium.Icon(               
                        color=colormap[cap_mod],
                        icon_color='#lightgreen',
                        icon='bicycle', 
                        prefix='fa')
                    ).add_to(directions_map)

            else:
                pop_up= folium.Popup('Station ' + str(row['id']) + ': ' + row['name'], max_width=150,min_width=150)
                folium.Marker([float(row['lat']), float(row['long'])], 
                popup=pop_up,
                icon=folium.Icon(
                    color=colormap_loc[CM2[row['city']]],
                    icon_color='#lightgreen',
                    icon='bicycle', 
                    prefix='fa')
                ).add_to(directions_map)

    return directions_map

def changeMapFocus(area, station, direction):
    area_to_longlat ={}
    area_to_zoom = {}
    
    area_to_longlat["All"] = [[37.329732,-122.418954],[37.804770,-121.877349]]
    area_to_zoom["All"] = 12
    
    
    area_to_longlat["San Francisco"] = [[37.771058, -122.418954], [37.80477, -122.388013]]   
    #area_to_longlat["San Fransisco"] = [37.79, -122.40]
    area_to_zoom["San Francisco"] = 14
    
    area_to_longlat["San Jose"] = [[37.329732, -121.905733], [37.352601, -121.877349]]
    #area_to_longlat["San Jose"] = [37.345, -121.885]
    area_to_zoom["San Jose"] = 14
    
    area_to_longlat["Palo Alto"] = [[37.4256839, -122.164759], [37.448598, -122.13777749999998]]
    #area_to_longlat["Palo Alto"] = [37.435, -122.151]
    area_to_zoom["Palo Alto"] = 14
    
    area_to_longlat["Mountain View"] = [[37.385956, -122.108338], [37.40694000000001, -122.066553]]
    #area_to_longlat["Mountain View"] = [37.395, -122.0851]
    area_to_zoom["Mountain View"] = 14
    
    area_to_longlat["Redwood City"] = [[37.481758, -122.236234], [37.491269, -122.203288]]
    #area_to_longlat["Redwood City"] = [37.485, -122.222]
    area_to_zoom["Redwood City"] = 15
    
    coordinates_plot = area_to_longlat[area]
    zoom_plot = area_to_zoom[area]
    
    map_object = plotgeneralMap(area, station, direction)
    map_object.fit_bounds(coordinates_plot)
    
    return map_object

# changeMapFocus(m, "San Jose")
# app.layout = html.Div(
#     [
#     # dcc.Store("memory-data", "data"),
#     html.Div(dcc.Dropdown(
#                 id='city-dropdown',
#                 options=[
#                     {'label': i, 'value': i} for i in unique_city],
#                 value='All',
#                 clearable = False,
#                 placeholder="Select a City",
#                 style=dict(
#                 width='100%')
#                 )
#             ),        
#     html.Iframe(id="map"),
#     ]
# )

# @app.callback(
#     [Output("map", "srcDoc")],
#     [Input("city-dropdown", "value")]
# )
# def update_map(city, station): #, is_open):
#     map_zoom = changeMapFocus(city)
#     map_zoom.save("trips_map.html")
#     return [open('trips_map.html', 'r').read()] #map_zoom._repr_html_() #open("trips_map.html", "r").read()

# if __name__ == "__main__":
#     app.run_server(debug=True)