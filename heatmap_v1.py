# hidden all the duplicate ID components

# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html

from dash.dependencies import Input, Output, ClientsideFunction

import pandas as pd
import dash_table
from dash.dependencies import Input, Output

import os
import numpy as np
import datetime
from datetime import datetime as dt
from datetime import timedelta
from dateutil.relativedelta import relativedelta

print("heatmap_v1.py")
# enriched_trip_data = pd.read_csv('enriched_trip_data.csv')
# Read Data
# df = pd.read_csv('enriched_trip_data.csv')
df = pd.read_csv('less_trips.csv')
status = pd.read_csv('status.csv')
raw_station_data = pd.read_csv('station.csv')
all_stations = list(raw_station_data['name'])
all_stations.insert(0, "All")

df['end_date'] = pd.to_datetime(df['end_date'], format="%Y-%m-%d %H:%M")
df['start_date'] = pd.to_datetime(df['start_date'], format="%Y-%m-%d %H:%M")

# datetime object containing current date and time
now = dt.now() #datetime.datetime(2020, 3, 10, 13, 30) # dt.now()
new_date = now - relativedelta(years=5) # if we change current time to 6 years ago
new_weekday = new_date.weekday()
dt_string = new_date.strftime("%Y-%m-%d %H:%M:%S")

# for heatmap 
start_HM_date=(new_date - timedelta(7)).replace(hour=0, minute=0, second=0, microsecond=0)#.datetime(d.year, d.month, d.day) # a week ago
end_HM_date=(new_date).replace(hour=0, minute=0, second=0, microsecond=0)

unique_city = df['start_city'].unique().tolist()
unique_city.append("All")
# get the stations nested in the cities with their dock count

def get_station_details(identity, station, dock_count):
    this_dict = {}
    this_dict['id']=identity,
    this_dict['name']=station
    this_dict['dock_count'] = dock_count
    return this_dict

raw_station_data['station_details'] = raw_station_data.apply(lambda x: get_station_details(x['id'], x['name'],x['dock_count']),axis=1)
station_cities = raw_station_data.groupby('city')['station_details'].apply(list).to_dict()

# print(station_cities)
for k in station_cities:
    curr_dict = station_cities[k]
    curr_dict.insert(0, {'id': 0, 'name': 'All', 'value': 'All'})
    station_cities[k] = curr_dict

day_list = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
# day_list.insert(new_weekday, "Today")

def get_heatmap_data(df, city_filter, station_filter, direction):
     # if there's no specific city
    print("direction is : " + direction)
    # if specific station
    if (station_filter!='All'):
        if (direction == "start"):
            filtered_df_1 = df[(df["start_station_name"]==station_filter)]
        elif (direction == "end"):
            filtered_df_1 = df[(df["end_station_name"]==station_filter)]
        else:
            filtered_df_1 = df[(df["start_station_name"]==station_filter) | (df["end_station_name"]==station_filter)]    
    else:
        if (city_filter!="All"):
            filtered_df_1 = df[(df["start_city"] == city_filter)]    
        else: # no stations
            filtered_df_1 = df
    # memory constrain
    # filtered_df = filtered_df_1.sort_values('end_date').set_index("end_date")[start_HM_date:end_HM_date]

    filtered_df = filtered_df_1[(filtered_df_1['end_date'] >= start_HM_date) & (filtered_df_1['end_date'] <= end_HM_date)]

    return filtered_df, filtered_df_1

def generate_trip_volume_heatmap(city_filter, station_filter, direction):
    """
    :param: city_filter: city from selection.
    :param: station_filter: station from selection.
    :return: Trips volume annotated heatmap.
    """
    filtered_df, filtered_df_1 = get_heatmap_data(df, city_filter, station_filter, direction)

    x_axis = [datetime.time(i).strftime("%I %p") for i in range(24)]  # 24hr time list
    y_axis = day_list

    hour_of_day = ""
    weekday = ""
    shapes = []
    hm_click = None

    if hm_click is not None:
        hour_of_day = hm_click["points"][0]["x"]
        weekday = hm_click["points"][0]["y"]
        # print(hour_of_day, weekday)
        # Add shapes
        x0 = x_axis.index(hour_of_day) / 24
        x1 = x0 + 1 / 24
        y0 = y_axis.index(weekday) / 8 #7
        y1 = y0 + 1 / 8 #7
        
        shapes = [
            dict(
                type="rect",
                xref="paper",
                yref="paper",
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
                line=dict(color="#ff6347"),
            )
        ]
    # current time!
    else:
        hour_of_day = datetime.time(new_date.hour).strftime("%I %p")
        
        # Add shapes
        x0 = x_axis.index(hour_of_day) / 24
        x1 = x0 + 1 / 24
        # y0 = y_axis.index(weekday) / 8 #7
        # y1 = y0 + 1 / 8 #7
        y0 = 7/8 #7
        y1 = 8/8 #7
        
        shapes = [
            dict(
                type="rect",
                xref="paper",
                yref="paper",
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
                line=dict(color="#ff6347"),
            )
        ]

    # Get z value : sum(number of records) based on x, y,

    # z = np.zeros((7, 24)) # 7 days, 24 hours
    z = np.zeros((8, 24)) # 8 days including today, 24 hours    
    # annot_dates = np.empty((8, 24), str)

    annotations = []
    dates = [(start_HM_date + timedelta(i)).strftime("%d %b") for i in range(0,7)] # last one should be today's
    # make today the last one always
    # the first input/day taken would be the last row on the heatmap
    # filtered df doesn't include end date - it includes till the last date
    
    if (new_weekday == 0):
        arrange_days = y_axis[::-1] # reverse 
        # annot_dates = dates[::-1]

    else:
        arrange_days = y_axis[new_weekday-1::-1] + y_axis[:new_weekday-1:-1]

    for ind_y, day in enumerate(arrange_days):
        filtered_day = (filtered_df[filtered_df["start_date_weekday_mtwtfss"] == day])
        for ind_x, x_val in enumerate(x_axis):
            count_of_trips = len(filtered_day[filtered_day["start_date_hour"] == ind_x])

            z[ind_y][ind_x] = count_of_trips
            # annot_dates[ind_y][ind_x] = (start_HM_date + timedelta(ind_y)).strftime("%d %b")

            annotation_dict = dict(
                showarrow=False,
                text="<b>" + str(count_of_trips) + "<b>",
                xref="x",
                yref="y",
                x=x_val,
                y=day, # + '\n' + (start_HM_date + timedelta(ind_y)).strftime("%d %b"),
                customdata = (start_HM_date + timedelta(ind_y)).strftime("%d %b"),
                font=dict(family="sans-serif"),
            )
            # Highlight annotation text by self-click
            if x_val == hour_of_day and day == weekday:
                if not reset:
                    annotation_dict.update(size=15, font=dict(color="#ff6347"))

            annotations.append(annotation_dict)

    # print(filtered_df.columns)
    add_today = filtered_df_1[(filtered_df_1['start_date_year'] == new_date.year) & (filtered_df_1['start_date_month']==(new_date.month)) & (filtered_df_1['start_date_day']==new_date.day)]
    # print(add_today)

    for ind_x, x_val in enumerate(x_axis[:new_date.hour+1]): # need to change this to make it more real time
        count_of_trips = len(add_today[add_today["start_date_hour"] == ind_x])
        # latest row
        z[7][ind_x] = count_of_trips
        # annot_dates[7][ind_x] = new_date.strftime("%d %b")

        annotation_dict = dict(
            showarrow=False,
            text="<b>" + str(count_of_trips) + "<b>",
            xref="x",
            yref="y",
            x=x_val,
            y='Today',
            customdata = new_date.strftime("%d %b"),
            font=dict(family="sans-serif"),
        )
        if x_val == hour_of_day and day == 'Today':
            if not reset:
                annotation_dict.update(size=15, font=dict(color="#ff6347"))

        annotations.append(annotation_dict)

    # Heatmap
    hovertemplate = "<b> %{y}  %{x}  <br> %{customdata} <br> %{z} Trips taken"
    # hovertemplate = "<b> %{}  %{}  <br> %{} <br> %{} Trips taken".format(y, x, day_week, z)
    # print("annotations in HM")
    # print(annotations)
    arrange_days.append('Today')
    dates = dates[::-1] # 8 days including today, 24 hours
    dates.append(new_date.strftime("%d %b"))
    y_axis_labels = [m + os.linesep + str(n) for m,n in zip(arrange_days, dates)]

    annot_dates = []
    for i in range(0,8):
        annot_dates.append([dates[i] for j in range(0,24)])

    # annot_dates = [[dates[j] for j in range(0,8)] for i in range (0,24)]
    # print(z)
    # print(annot_dates)
    # print(len(annot_dates))

    data = [
        dict(
            x=x_axis,
            y= arrange_days, #y_axis_labels, #arrange_days, #y_axis_labels, # arrange_days + ['Today'],
            z=z,
            customdata = annot_dates, #[dates for i in range (0,24)], #annot_dates, #annot_dates, #dates, # making it a list of list
            type="heatmap",
            name="",
            hovertemplate=hovertemplate,
            showscale=False,
            colorscale=[[0, "rgb(224,243,248)"], [1, "rgb(69,117,180)"]],
        )
    ]

    layout = dict(
        margin=dict(l=70, b=50, t=50, r=50),
        modebar={"orientation": "v"},
        font=dict(family="Open Sans"),
        annotations=annotations,
        shapes=shapes,
        xaxis=dict(
            side="top",
            ticks="",
            ticklen=2,
            tickfont=dict(family="sans-serif"),
            tickcolor="#ffffff",
        ),
        yaxis=dict(
            values=[y_axis_labels],
            side="left", ticks="", tickfont=dict(family="sans-serif"), ticksuffix=" "
        ),
        hovermode="closest",
        showlegend=True,
    )
    return {"data": data, "layout": layout}