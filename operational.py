import requests
import pandas as pd
import numpy as np
from flask import Flask
import dash
from dash.dependencies import Input, Output, State
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

import datetime
from datetime import datetime as dt
from datetime import timedelta
from dateutil.relativedelta import relativedelta

import folium

# to make code more tidy
from heatmap_v1 import generate_trip_volume_heatmap 
from row1_functions import count_trips, difference_in_trips, trips_in_progress, get_station_info, get_routes,get_weather, get_status_table
from folium_map import changeMapFocus

print("main.py")

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
# app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
app.config.suppress_callback_exceptions = True
baywheels_logo = "https://upload.wikimedia.org/wikipedia/en/thumb/9/95/Bay_Wheels_logo.png/200px-Bay_Wheels_logo.png"


#########################
# Preprocess Data
#########################
# df = pd.read_csv('enriched_trip_data.csv')
df = pd.read_csv('less_trips.csv') # 2015 data only
raw_station_data = pd.read_csv('station.csv')
weather = pd.read_csv('cleaned_weather_and_temperature_data.csv')
status_73 = pd.read_csv("status_73.csv") #, format="%Y-%m-%d %H:%M")
df['end_date'] = pd.to_datetime(df['end_date'], format="%Y-%m-%d %H:%M")
df['start_date'] = pd.to_datetime(df['start_date'], format="%Y-%m-%d %H:%M")

# city filter
unique_city = df['start_city'].unique().tolist()
unique_city.append('All')
# station filter
all_stations = list(raw_station_data['name'])
# all_stations.insert(0, "All")

# get current date and time
# now = datetime.datetime(2020, 3, 10, 13, 30) # dt.now()
now = dt.now()
new_date = now - relativedelta(years=5) # if we change current time to 6 years ago
new_datetime = dt.combine(new_date, datetime.time(0,0))

new_weekday = new_date.weekday()
# format datetime to: 9 Mar 2015, Monday  1:30 PM (date, day, time)
formatted_dt = new_date.strftime("%d %b %Y, %A, %I:%M%p")
formatted_data_dt = new_date.strftime("%m/%d/%Y %H:%M") # for the goals

# # for heatmap to set the dates
start_HM_date=(new_date - timedelta(7)).date() # a week ago
end_HM_date=(new_date).date()

# tmr date
tmrdate = new_date + timedelta(days=1)
tmrdatetime = dt.combine(tmrdate, datetime.time(0,0))

# compare it to ystd
yesterdate = new_date - timedelta(days=1)
yesterdatetime = dt.combine(yesterdate, datetime.time(0,0))

# for the prediction model
# status_67 = pd.read_csv('SF_35_stations_status_file/station_67_status_data.csv')

status_73['time'] = pd.to_datetime(status_73['time'])
status_73['time'] = status_73['time'].dt.round('1min') # rounded off to the nearest min

# to get the station
def get_station_details(identity, station, dock_count):
    this_dict = {}
    this_dict['id']=identity,
    this_dict['name']=station
    this_dict['dock_count'] = dock_count
    return this_dict

# for the station-city dropdown
raw_station_data['station_details'] = raw_station_data.apply(lambda x: get_station_details(x['id'], x['name'],x['dock_count']),axis=1)
station_cities = raw_station_data.groupby('city')['station_details'].apply(list).to_dict()

day_list = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

# input id
def get_city_from_station(station): 
    city = raw_station_data[raw_station_data["id"]==station]["city"]
    return city.values[0]

def goal(yr, week_nr):
    year_week = df.groupby(["start_date_year", "start_date_week"])
#     this_week = len(year_week.get_group((yr, week_nr)))
    count = 0
    for i in range(1,5):
        count += len(year_week.get_group((yr, week_nr-i)))
    return round(count/4)

the_year, week_nr = new_date.isocalendar()[0], new_date.isocalendar()[1]
trips_thisweek = df[(df['start_date_year']==the_year) & (df['start_date_week']==week_nr) & (df['end_date']<=formatted_data_dt)]
goalie = goal(the_year, week_nr)
progress = round(len(trips_thisweek)*100/goalie, 1)


#########################
# Navigation Bar
#########################
navbar = dbc.Navbar(
    [
        dbc.Col(html.A(
            html.Img(src=baywheels_logo, height="60px"), href="https://www.lyft.com/bikes/bay-wheels",
                ), width=1.5,
            ),
        dbc.Col(
            dbc.NavbarBrand("Operational Dashboard", className="ml-2")
            ),
        dbc.Col(
            # dbc.NavItem(
            dbc.Card(formatted_dt, style={"width": "275px", "height": "30px", "textalign": "middle"})
            ), # width=3
            # ),
        dbc.Col(
            # dbc.NavItem(
                [
                html.Span("Select City"),
                dcc.Dropdown(
                    id='city-dropdown',
                    options=[
                        {'label': i, 'value': i} for i in sorted(unique_city)],
                    value='All',
                    clearable = False,
                    placeholder="Select a City",
                    style=dict(
                    width='100%')
                    )
                ], width=2,
            ),        

        dbc.Col(
            dbc.Nav(dbc.NavLink("KPI Dashboard", href="KPI"), navbar=True), 
            width="auto"
            ),
    ], className="mb-5",
)

# custom navbar based on https://getbootstrap.com/docs/4.1/examples/dashboard/

#########################
# Big indicators on performance
#########################
row1 = dbc.Row(
    [dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.H5(id="trips_completed_number"), 
                    html.Span(dbc.Badge(id="diff_in_trips_percent", style={'display': 'inline-block'})), 
                    html.P(
                            id="card1-text",
                            className="card-text",
                        ),
                    # indicator graph that was hard to resize
                    # dcc.Graph(id="trips_completed_number",)
                ]),
            )
    ),
    dbc.Col(dbc.Card(
            dbc.CardBody(
                    [
                        html.H5(id="trips_in_prog_number"),
                        html.P(
                            "Trips in Progress",
                            className="card-text",
                        ),
                    ]
                )
            ),
    ),
    dbc.Col(dbc.Card(
            dbc.CardBody(
                    [
                        html.H5(id="weather", className="card-title"),
                        html.P(
                            id="weather-city",
                            className="card-text",
                        ),
                    ]
                )
            ),
    ),
    dbc.Col(dbc.Card(
            dbc.CardBody(
                    [
                        html.H5("Progress of Weekly Performance", className="card-title"),
                        html.P(children=[
                            html.Span("Average weekly trips taken is: "),
                            html.Strong(str(goalie)),
                            html.Span(" trips (" + str(len(trips_thisweek)) + " trips now)")]
                        ),
                        dbc.Progress(str(progress)+"%", value=progress, striped=True),

                    ]
                )
            )
    )]
)

# formatted to the html version but it didn't look presentable
# row1 = html.Div([
#         html.Div(
#             children=[
#                 html.Div(
#                     [
#                         html.H6(
#                             id="card1-text",
#                             className="card-text",
#                         ),
#                         dcc.Graph(id="trips_completed_number")
#                     ],
#                     className="pretty_container"
#                 ),
#                 html.Div(
#                     [
#                         html.H5(id="trips_in_prog_number"),
#                         html.H6(
#                             "Trips in Progress"
#                         ),
#                     ],
#                     className="pretty_container"
#                 ),
#                 html.Div(
#                     [
#                         html.H5(id="weather", className="card-title"),
#                         html.H6(id="weather-city"),
#                     ],
#                     className="pretty_container"
#                 ),
#                 html.Div(
#                     [
#                         html.H6("Progress of Weekly Performance"),
#                         html.P(children=[
#                             html.Span("Average weekly trips taken is: "),
#                             html.Strong(str(goalie)),
#                             html.Span(" trips")],
#                         ),
#                         dbc.Progress(str(progress)+"%", value=progress, striped=True),
#                     ],
#                     className="pretty_container"
#                 ),
#             ],
#             id="fourContainer"
#         )
#     ]
# )

#########################
# Folium Map and Heatmap
#########################
row2 = dbc.Row(
    [dbc.Col([
        html.Div([
            html.P("Select Station"),
            dcc.Dropdown(
                id="station-dropdown",
                value= 'All',
                clearable = True,
                placeholder = "Select a Station"
            ),], style={'width': '48%', 'display': 'inline-block'}),
        html.Div([
            html.P("Select Direction"),
            dbc.RadioItems(
                options=[
                    {'label': 'Both', 'value': 'both'},
                    {'label': 'Arrival', 'value': 'start'},
                    {'label': 'Departure', 'value': 'end'},
                    ],
                value= 'both',
                id="direction-radio",     
                inline=True,
            ),], style={'width': '48%', 'display': 'inline-block'}),

        html.Br(),
        html.Iframe(id="map", width=820, height=400),
        ], width=6, className="pretty_container", 
    ),
    dbc.Col(html.Div(
                id="patient_volume_card",
                children=[
                    html.B("Trips Volume across the week"),
                    html.P(children=[
                        html.Span(id="hm-text"),
                        html.Strong(str(start_HM_date) + " to " + str(end_HM_date) + " (Today)")]
                        ),
                    html.Hr(),
                    dcc.Graph(id="trips_volume_hm"),
                ],
            )
    )])

# Row 3: Data Table and the Line Graph prediction

# prediction line graph
today_73 = status_73[(status_73['time']<tmrdatetime)&(status_73['time']>=new_datetime)]
# print(today_73.head())
# print(today_73.describe())
# today_67 = status_67[(status_67['time']<tmrdatetime)&(status_67['time']>=new_datetime)]
# ystd_67 =  status_67[(status_67['time']<new_datetime)&(status_67['time']>=yesterdatetime)]
# lastweek_67 = status_67[(status_67['time']<(new_datetime-timedelta(days=7)))&(status_67['time']>=yesterdatetime-timedelta(days=7))]

docks_73 = raw_station_data[raw_station_data["id"]==73]['dock_count'].values[0]
rounded_time = new_date - datetime.timedelta(minutes=new_date.minute % 10,
                             seconds=new_date.second, #data pulled every 2 secs
                             microseconds=new_date.microsecond)

current_bikes = today_73[today_73['time']==rounded_time]['bikes_available']
capacity = round((current_bikes.values[0]/docks_73)*100)

# this was using Plotly Go Figure, but it wasn''t as flexible
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=today_73['time'].dt.time, 
        y=today_73['bikes_available'], 
        name="Today", 
        line_color='deepskyblue'
        )
    )
# fig.add_shape( # error loading layout
#         # Current time line
#             type="line",
#             x0=new_date.time,
#             y0=0,
#             x1=new_date.time,
#             y1=docks_73, # reach the bike cap
#             line=dict(
#                 color="MediumPurple",
#                 width=4,
#                 dash="dot",
#             )
#         )
# fig.update_shapes(dict(xref='x', yref='y'))
# doesn't work too
# fig.add_trace(go.Scatter(x=[new_date.time], y=[0], name='Current Time',
#                          line=dict(color='blue', dash='dashdot'))) # current time
fig.update_layout(
    title_text='Prediction of the Number of bikes at Grant Avenue at Columbus Avenue',
    xaxis = dict(constrain="domain"),
    )

def bikes_avail_data(station):
    data = [
        dict(
            type='scatter',
            mode='lines+markers',
            name='Bikes Available Today',
            x=list(today_73['time'].dt.time),
            y=list(today_73['bikes_available']),
            line=dict(
                shape="spline",
                smoothing=2,
                width=1,
            ),
            # marker=dict(symbol='diamond-open')
        )
    ]
    layout = dict(
        autosize=True,
        automargin=True,
        margin=dict(
            l=30,
            r=30,
            b=20,
            t=40
        ),
        hovermode="closest",
        plot_bgcolor="#F9F9F9",
        paper_bgcolor="#F9F9F9",
        legend=dict(font=dict(size=10), orientation='h'),
        title='Prediction of Bikes Available at ' + station,
        # shapes=[ # doesn't let me plot my layout after doing this
        # {'type': 'line',
        #            'xref': 'x',
        #            'yref': 'y',
        #            'x0': new_date.time,
        #            'y0': 0,
        #            'x1': new_date.time,
        #            'y1': docks_73,
        #            'line': dict(
        #             color="MediumPurple",
        #             dash="dot")
        # }]

    )
    # layout_line.update(vline=new_date.time)
    figure = dict(data=data, layout=layout)
    # figure.add_shape( # doesn't have this ability
    #     # Line Diagonal
    #         type="line",
    #         x0=new_date.time,
    #         y0=0,
    #         x1=new_date.time,
    #         y1=docks_73, # extend throughout
    #         line=dict(
    #             color="MediumPurple",
    #             width=4,
    #             dash="dot",
    #         )
    # )
    return figure

bikes_avail = dcc.Graph( 
        id='bikes_avail',
        figure = fig, #bikes_avail_data("Market at 10th")
    )

#########################
# status Tables and Prediction
#########################
row3 = dbc.Row(
    [
        # dbc.Col([
        html.Div([
            html.B(id="table-name"),
            html.Hr(), 
            html.P(id="benchmark-info"),    
            dcc.Graph(id="stations-table"),
            ], id="hide-table", className="pretty_container",
        ),
        dbc.Col(bikes_avail, width = 5),
        dbc.Col(
            [
            dbc.Row(dbc.Card(
            dbc.CardBody(
                    [
                        html.H5(
                            current_bikes, style={'textalign': 'center'},
                            # className="card-text",
                        ),
                        html.P("Current Bikes Available", className="card-title"),
                    ]
                ), color="info", outline=True, id="67-bikes")),
            html.Br(),
            dbc.Row(dbc.Card(
            dbc.CardBody(
                    [
                        html.H5(str(capacity) + "%", style={'textalign': 'center'},),
                        html.P("Dock Capacity", className="card-title"),
                    ]
                ), color="info", outline=True, id="67-cap")
                ),
            ],
        width = 1)
    ]
    )

cards = html.Div([row1, row2, row3])


app.layout = html.Div(
    [
    navbar,
    cards,
    ]
)

##### CALLBACKS ######

# Station - City callback
@app.callback(
    Output('station-dropdown', 'options'),
    [Input('city-dropdown', 'value')])
def set_cities_options(selected_city):
    if (selected_city=="All"):
        options_cities = [{'label': i, 'value': i} for i in sorted(all_stations)]
        options_cities.insert(0, {'label': 'All', 'value': 'All'})
        return options_cities

    else:
        that_city = station_cities[selected_city]
        # print(that_city)
        options_stations = [{'label': i['name'], 'value': i['name']} for i in sorted(that_city, key=lambda x: x['name'])]
        # print(options_stations)
        options_stations.insert(0, {'label': 'All', 'value': 'All'})
        return options_stations
        # return [{'label': i['name'], 'value': i['name']} for i in sorted(that_city, key=lambda x: x['name'])]

# dynamic stations from City
@app.callback(
    Output('station-dropdown', 'value'),
    [Input('station-dropdown', 'options')])
def set_cities_value(available_options):
    return available_options[0]['value'] #, get_city_from_station(available_options[0]['label']) #default: 'All'

# card1 row1
@app.callback(
    [Output("trips_completed_number", "children"),
    # [Output("trips_completed_number", "value"),
    # [Output("trips_completed_number", "figure"),
    Output("card1-text", "children"),
    Output("diff_in_trips_percent", "children"),
    Output("diff_in_trips_percent", "color"),
    Output("trips_in_prog_number", "children"),
    ],
    [Input("city-dropdown", "value"),
     Input("station-dropdown", "value"),
     Input("direction-radio", "value")],
)
def update_trips_completed(city, station, direction):
    trips_completed = count_trips(city, station, direction)
    ref = count_trips(city, station, yesterdate) 

    if (station!="All"):
        if (direction == "both"):
            text1 = "Trips started and ended from " + str(station)
        elif (direction == "start"):
            text1 = "Trips started from " + str(station)
        else:
            text1 = "Trips ended at " + str(station) 
    elif (city!="All"):
        text1="Completed Trips today at " + city
    else:
        text1="Completed Trips today"    

    diff_in_trips_percent = difference_in_trips(city, station, direction)

    # badge colour and formatting of the percentage
    if (diff_in_trips_percent<0):
        colour = "danger"
        diff_in_trips_percent = "-" + str(diff_in_trips_percent) +"%"
    elif (diff_in_trips_percent ==0):
        colour = "warning"
        diff_in_trips_percent = str(diff_in_trips_percent) +"%"
    else:
        colour = "success"
        diff_in_trips_percent = "+" + str(diff_in_trips_percent) +"%"

    # print("trips in prog:")
    trips_in_prog_number = trips_in_progress(city, station)
    
    return trips_completed, text1, diff_in_trips_percent, colour, trips_in_prog_number    
    # return fig, text1, trips_in_prog_number


@app.callback(
    [Output("weather", "children"),
    Output("weather-city", "children")],
    [
        Input("city-dropdown", "value"),
        Input("station-dropdown", "value")
    ],
)
def update_weather(city, station):
    # Assuming that the HQ is at SF
    if ((city == "All") & (station == "All")):
        return get_weather("San Francisco"), "Weather in San Francisco HQ"
    elif (station == "All"): # city is chosen
        return get_weather(city), ("Weather in " + city)
    else:
        station_id = get_station_info("id", station)
        get_city = get_city_from_station(station_id)
        return get_weather(get_city), ("Weather in " + get_city)

# # FOLIUM MAP call back
@app.callback(
    [Output("map", "srcDoc")],
    [Input("city-dropdown", "value"),
    Input("station-dropdown", "value"),
    Input("direction-radio", "value"),]
)
def update_map(city, station, direction): 
    if ((station != "All")):
        station_id = get_station_info("id", station)
        get_city = get_city_from_station(station_id)
        city = get_city
    print(city)
    map_zoom = changeMapFocus(city, station, direction)
    map_zoom.save("trips_map.html")
    return [open('trips_map.html', 'r').read()]

# Heatmap call back
@app.callback(
    [Output("trips_volume_hm", "figure"),
    Output("hm-text", "children")],
    [
        Input("city-dropdown", "value"),
        Input("station-dropdown", "value"),
        Input("direction-radio", "value"),
    ],
)
def update_heatmap(city, station, direction):
    if (station=="All"):
        text1 = "Trips taken today compared to the trips over the past week: "
    elif (direction == "both"):
        text1 = "Trips started and ended from" + str(station) + " today compared to the trips over the past week: "
    elif (direction == "start"):
        text1 = "Trips started from " + str(station) + " today compared to the trips over the past week: "
    else:
        text1 = "Trips ended at " + str(station) + " today compared to the trips over the past week: "
    
    return generate_trip_volume_heatmap(city, station, direction), text1

@app.callback(
    [Output('stations-table', 'figure'),
     Output("table-name", "children"),
     Output("benchmark-info", "children")],
    [Input("city-dropdown", "value"),
     Input("station-dropdown", "value"),
     Input("direction-radio", "value"),])
def update_stationtable(city, station, direction):
    # no specific station
    if (station == "All"): 
        stations_table, benchmark = get_status_table()

        figure = go.Figure(data=[go.Table(
            columnwidth = [200 ,100, 100, 10, 200 ,100, 100],
            header=
                dict(values=list(stations_table.columns),
                # lightgreen: #90EE90   
                # tomato: #FF6347
                # white: #FFFFFF
                # lightlue bg: #D2F1FC
                fill=dict(color=['#90EE90', '#90EE90','#90EE90', '#FFFFFF', '#FF6347', '#FF6347', '#FF6347']),
            ),
            cells=dict(
                values=[stations_table["Excess Station Names"], stations_table["75th Percentile capacity"], stations_table["Bikes Available"], stations_table["."], stations_table["Risky Station Names"], stations_table["25th Percentile capacity"], stations_table["Bikes Left"]],
                fill=dict(color=['#D2F1FC', '#D2F1FC','#D2F1FC', '#FFFFFF', '#D2F1FC', '#D2F1FC', '#D2F1FC']),
                )
            )   
        ])

        benchmark_info = "Capacity considered safe: " + str(benchmark[0.75]) +"% ; " + "Capacity considered risky: " + str(benchmark[0.25]) + "%"

        if (city=="All"):
            text1 = "Current Stations Outlook"
        elif (city=="San Francisco"): # only have data for SF for now
            text1 = "Current Stations Outlook in " + city
        else:
            # no data for other cities
            figure = go.Figure(data=[go.Table(
                header=
                    dict(values=list(["No data available"])),
                cells=dict(
                    values=["No data available"],
                    )
                )   
            ])
            return figure, "Status Outlook coming soon" , ""
        
        return figure, text1, benchmark_info        
            
    # specific stations data
    else:
        text1 = "Trips taken to and from " + str(station)
        
        print("specific station")
        routes_data = get_routes(city, station, direction)
    
        figure = go.Figure(data=[go.Table(header=dict(values=list(routes_data.columns),
                                            fill_color='paleturquoise',
                                            align='center'),
                                            cells=dict(
                                                # values=[routes_data["Start Station"], routes_data["End Station"], routes_data["Count"], routes_data["Average Duration (mins)"]],
                                                values=[routes_data[col] for col in routes_data.columns],
                                                align='left'))])
        return figure, text1
    
@app.callback(
    [Output("bikes_avail", "style"),
    Output("67-bikes", "style"),
    Output("67-cap", "style")],
    [Input("station-dropdown", "value")]
)
def open_prediction(station): 
    if (station!="Grant Avenue at Columbus Avenue"): # station 73
        # return not is_open
        return {'display': 'none'}, {'display': 'none'}, {'display': 'none'}
    return {'display': 'block'}, {'display': 'block'}, {'display': 'block'}
    
@app.callback(
    Output("hide-table", "style"),
    [Input("city-dropdown", "value"), Input("station-dropdown", "value")]
)
def open_table(city, station): 
    # if all cities then hide
    if ((city=="All") & (station=="All")):
        # return not is_open
        return {'display': 'none'}
    # if specific station
    else:        
        return {'display': 'block'}
    
   

if __name__ == "__main__":
    app.run_server(debug=True)