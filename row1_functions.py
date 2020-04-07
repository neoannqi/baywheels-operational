import requests
import pandas as pd
import dash_table
import os
import numpy as np

import datetime
from datetime import datetime as dt
from datetime import timedelta
from dateutil.relativedelta import relativedelta

print("row1_functions.py")

#########################
# Read in Data
#########################
# df = pd.read_csv('enriched_trip_data.csv')
df = pd.read_csv('less_trips.csv')
raw_station_data = pd.read_csv('station.csv')
weather = pd.read_csv('cleaned_weather_and_temperature_data.csv')
# status = pd.read_csv('Mar15_SF_name.csv')
df['end_date'] = pd.to_datetime(df['end_date'], format="%Y-%m-%d %H:%M")
df['start_date'] = pd.to_datetime(df['start_date'], format="%Y-%m-%d %H:%M")
status_apr = pd.read_csv("SF_status_apr15.csv")
#########################
# Preprocess Data
#########################

# datetime object containing current date and time
# now = datetime.datetime(2020, 3, 10, 13, 30) # dt.now()
now = dt.now()
new_date = now - relativedelta(years=5) # if we change current timedelta to 6 years ago

new_weekday = new_date.weekday()
dt_string = new_date.strftime("%d/%m/%Y %H:%M:%S")

# tmr date
tmrdate = new_date + timedelta(days=1)
tmrdatetime = dt.combine(tmrdate, datetime.time(0,0))

# compare it to ystd
yesterdate = new_date - timedelta(days=1)
yesterdatetime = dt.combine(yesterdate, datetime.time(0,0))

# compare it to last week
lastweekdate = new_date - timedelta(days=7)

#########################
# Creating functions
#########################

# Function: Edit the dataframe, will be used in most functions to get the right data
# Input: df, city name, station name, date in dt format, whether the routes are from start or both stations, whether the data is to calculate the trips in progress, if I'm looking at start or end station
# Output: dataframe with the city, station and date filtered
def filter_dataframe(df, city, station, new_date, twoway=False, progress=False, start=True):
    new_datetime = dt.combine(new_date, datetime.time(0,0))
    station = get_station_info("id", station)
    # specific station data
    if (station!="All"):
        if twoway:
            dff = df[(df["start_station_id"] == station) | (df["end_station_id"] == station)]
        elif (start):
            dff = df[(df["start_station_id"] == station)]
        else:
            dff = df[(df["end_station_id"] == station)]
    # all city specific
    elif (city!="All" and station == "All"):
        if twoway:
            dff = df[(df["start_station_id"] == station) | (df["end_station_id"] == station)]
        dff = df[(df['start_city'] == city)]

    else:
        dff = df

    # filter by time
    if (progress): # progress won't have 2 ways
        dfff = dff[(dff['end_date'] > new_date) & (dff['start_date'] <= new_datetime) & (dff['start_date'] <= new_date)]

    else:
        dfff = dff[(dff["end_date"] <= new_date) & (dff["start_date"] >= new_datetime)]
    return dfff

# Function: Count the length of data
# Input: city name, station name, date in dt format
# Output: length of dataset
def count_trips(city, station, direction, date=new_date):
    if (direction == "both"):
        trips_completed = filter_dataframe(df, city, station, date, twoway=True)
    elif (direction == "start"):
        trips_completed = filter_dataframe(df, city, station, date, start=True)
    else:
        trips_completed = filter_dataframe(df, city, station, date, start=False)
    return len(trips_completed)

# Function: counts the difference in trips between today and ystd
# Input: city name, station name, date in dt format
# Output: the percentage change from ystd to today
def difference_in_trips(city, station, direction):
    today_trips = count_trips(city, station, direction, date=new_date)
    ystd_trips = count_trips(city, station, direction, date=lastweekdate)
    diff = 0 if (ystd_trips==0) else ((today_trips - ystd_trips)/ystd_trips)
    return round(diff)

# Function: counts the difference in trips between today and ystd
# Input: city name, station name
# Output: the percentage change 
def trips_in_progress(city, station):
    data = filter_dataframe(df, city, station, new_date, progress=True)
    return len(data)

# # Dash Datatable
# def get_popstations(city):
#     trips_completed = filter_dataframe(df, city, "All", new_date)
#     start_comp = trips_completed["start_station_id"].value_counts()
#     end_comp = trips_completed["end_station_id"].value_counts()
#     comp_bystations = start_comp.add(end_comp, fill_value =0) # handles NaN in one df and not the other
#     comp_bystations = comp_bystations.rename_axis('id').reset_index(name='Trips')
#     print(len(comp_bystations)) # all have
#     popular_stations = comp_bystations.merge(raw_station_data, on='id')
#     popular_stations.rename(columns={'name': 'Station Name'}, inplace=True)
#     popular_stations = popular_stations[['Station Name', 'Trips']].sort_values(by='Trips', ascending=False)
#     return (popular_stations)

# def get_bottomstations(city):
#     trips_completed = filter_dataframe(df, city, "All", new_date)
#     start_comp = trips_completed["start_station_id"].value_counts()
#     end_comp = trips_completed["end_station_id"].value_counts()
#     comp_bystations = start_comp.add(end_comp, fill_value =0) # handles NaN in one df and not the other
#     comp_bystations = comp_bystations.rename_axis('id').reset_index(name='Trips')
#     bottom_stations = comp_bystations.merge(raw_station_data, on='id')
#     bottom_stations.rename(columns={'name': 'Station Name'}, inplace=True)
#     bottom_stations = bottom_stations[['Station Name', 'Trips']].sort_values(by='Trips', ascending=True)
#     return(bottom_stations)

# Function: To get the popular and unpopular stations
# Input: city name, station name
# Output: dataframe with the stations calculated
# def get_citytable(city, station):
#     trips_completed = filter_dataframe(df, city, "All", new_date)
#     start_comp = trips_completed["start_station_id"].value_counts()
#     end_comp = trips_completed["end_station_id"].value_counts()
#     comp_bystations = start_comp.add(end_comp, fill_value =0) # handles NaN in one df and not the other
#     comp_bystations = comp_bystations.rename_axis('id').reset_index(name='Trips')
#     popular_stations = comp_bystations.merge(raw_station_data, on='id')
#     popular_stations.rename(columns={'name': 'Station Name'}, inplace=True)
#     bottom_stations = popular_stations.copy()
#     popular_stations = popular_stations[['Station Name', 'Trips']].sort_values(by='Trips', ascending=False)
#     bottom_stations = bottom_stations[['Station Name', 'Trips']].sort_values(by='Trips', ascending=True)
#     bottom_stations.rename(columns={'Station Name': 'Name', "Trips": "Count"}, inplace=True)

#     final_df = pd.concat([popular_stations, bottom_stations], axis=1, sort=True)
#     return final_df

def get_status_table():
    # get the benchmark
    benchmark = status_apr["capacity"].quantile([.25, .75])
    current_info = status_apr[(status_apr["day"]== new_date.day) & (status_apr["hour"] == new_date.hour) & (status_apr["minute"] == new_date.minute)]
    current_info["name"] = current_info["station_id"].apply(lambda x: raw_station_data[raw_station_data["id"] == int(x)]["name"].values[0])
    more_cap = current_info[current_info["capacity"]>benchmark[0.75]][["name", "capacity", "bikes_available"]].sort_values(by="capacity", ascending=False).reset_index(drop=True)
    lack_cap = current_info[current_info["capacity"]<benchmark[0.25]][["name", "capacity", "bikes_available"]].sort_values(by="capacity", ascending=True).reset_index(drop=True)
    more_cap.rename(columns={"name": "Excess Station Names", "capacity": "75th Percentile capacity", "bikes_available": "Bikes Available"}, inplace=True)
    lack_cap.rename(columns={"name": "Risky Station Names", "capacity": "25th Percentile capacity", "bikes_available": "Bikes Left"}, inplace= True)
    # add a gap column
    more_cap["."]= ""
    status_table = pd.concat([more_cap, lack_cap], axis=1)
    status_table = status_table.replace(np.nan, '', regex=True)
    return status_table, benchmark

# info: 'name' or 'id'
def get_station_info(info, station_details):
    get = "name" if (info == "id") else "id"
    row = raw_station_data[raw_station_data[get] == station_details]
    result = row[info]
    if (len(result.values) == 0): # got the wrong id
        return station_details
    return result.values[0]

def get_routes(city, station, direction):
    print(city, station) # station should be id
    station_id = get_station_info('id', station)
    
    if (direction == "both"):
        trips_completed = filter_dataframe(df, city, station, new_date, twoway=True)
    elif (direction == "start"):
        trips_completed = filter_dataframe(df, city, station, new_date, start=True)
    else:
        trips_completed = filter_dataframe(df, city, station, new_date, start=False)
    
    # trips_bystation = trips_completed[(trips_completed['start_station_id']==station_id) | (trips_completed['end_station_id']==station_id)]
    
    # table showing the routes taken to and fro this station
    plot_dict = dict()
    inflow_outflow = {}

    for index,row in trips_completed.iterrows():
        key2 = get_station_info('name', row['start_station_id'])
        key3 = get_station_info('name', row['end_station_id'])
        key1 = (key2, key3) #str(key2)+'_'+str(key3)

        # count trips
        if key1 in plot_dict:   
            plot_dict[key1]["trips"] += 1
            plot_dict[key1]["duration"] += row["duration"]
        else:
            plot_dict[key1] = {"trips": 1, "duration": row["duration"]}
            
    start_id = map(lambda x: x[0],  plot_dict.keys())#map(lambda x: get_station_info('name', x[0]),  plot_dict.keys())
    end_id = map(lambda x: x[1],  plot_dict.keys()) # map(lambda x: get_station_info('name', x[0]),  plot_dict.keys())
    results = list(plot_dict.values())
    trips_count = list(i["trips"] for i in results)
    avg_duration = list(round(i["duration"]/(60*i["trips"])) for i in results)
    if (len(results)):
        routes_bystation = pd.DataFrame({'Start Station': list(start_id), 'End Station': list(end_id), "Count": trips_count, 'Average Duration (mins)': avg_duration})
        routes_bystation.sort_values(by=["Count", "Average Duration (mins)"], inplace=True, ascending=False)
    # if there were no routes
    else:
        # routes_bystation = pd.DataFrame(columns=['Start Station', 'End Station', "Count", "Average Duration (mins)"])
        # routes_bystation.loc[0] = ["", "No Trips from/to this Station yet", "", ""]
        routes_bystation = pd.DataFrame(columns=['No trips from this station yet'])
        routes_bystation.loc[0] = ["No Trips from/to this Station yet"]
    # print("dictionary: ")
    # print(plot_dict)
    # temporary = pd.DataFrame.from_dict(plot_dict, orient='index')
    return routes_bystation


def get_weather(city):
    # print(weather.info())
    weather["datetime"] = pd.to_datetime(weather["datetime"])
    nearest_hr = new_date.replace(minute=0, second=0, microsecond=0) 

    row = weather[weather["datetime"]==nearest_hr]
    temp = row["temperature"].values[0]
    desc = row["cleaned_descriptions"].values[0].capitalize() # make big first letter big
    return desc +", " + str(temp) + "°C"


## for the bikes availability station data
# def get_availability(city):
#     current_hour_status = status[(status["year"]==new_date.year) & (status["month"]==new_date.month) & (status["day"]==new_date.day)]
#     current_hour_status["capacity"] = round((current_hour_status["bikes_available"])*100/((current_hour_status["bikes_available"]+current_hour_status["docks_available"])))
#     