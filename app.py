import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go


# Define the directory for processed data files
data_dir = os.getenv('DATA_DIR', 'data_processed')

print(data_dir)

if not os.path.exists(data_dir):
    print(f"Data directory does not exist: {data_dir}")
    data_dir = None

# Initialize the Dash app with callback exceptions suppressed
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Environmental Data Dashboard"
server = app.server  # Expose the server variable for deployments
def load_data(directory, device):
    if directory is None or device is None:
        return pd.DataFrame()

    file_path = os.path.join(directory, f'{device}.csv')
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df[df['time'].notna()]
        return df

    return pd.DataFrame()

# Heat index calculation function (no changes needed)
def calculate_heat_index(temp_f, rh):
    c1 = -42.379
    c2 = 2.04901523
    c3 = 10.14333127
    c4 = -0.22475541
    c5 = -6.83783e-3
    c6 = -5.481717e-2
    c7 = 1.22874e-3
    c8 = 8.5282e-4
    c9 = -1.99e-6
    
    heat_index = (c1 + (c2 * temp_f) + (c3 * rh) + (c4 * temp_f * rh) +
                  (c5 * temp_f ** 2) + (c6 * rh ** 2) +
                  (c7 * temp_f ** 2 * rh) + (c8 * temp_f * rh ** 2) +
                  (c9 * temp_f ** 2 * rh ** 2))
    
     # Adjustment conditions
    if temp_f < 80 or rh < 40:
        # If the temperature is below 80°F or humidity below 40%, use a simpler equation
        heat_index = 0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (rh * 0.094))

    elif rh < 13 and 80 <= temp_f <= 112:
        # Adjustment for low humidity
        adjustment = ((13 - rh) / 4) * ((17 - abs(temp_f - 95)) / 17) ** 0.5
        heat_index -= adjustment

    elif rh > 85 and 80 <= temp_f <= 87:
        # Adjustment for high humidity
        adjustment = ((rh - 85) / 10) * ((87 - temp_f) / 5)
        heat_index += adjustment

    return heat_index  

# Function to format device names
def format_device_name(device_name):
    return device_name[-5:]

# Load initial data to set default date range
device_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
first_device = device_files[0][:-4] if device_files else None
initial_data = load_data(data_dir, first_device)


if not initial_data.empty and 'time' in initial_data.columns:
    default_start_date = initial_data['time'].min().date() if not initial_data['time'].isna().all() else None
    default_end_date = initial_data['time'].max().date() if not initial_data['time'].isna().all() else None
else:
    default_start_date = None
    default_end_date = None

# Main layout with dropdown navigation
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(className='container', children=[
        html.H1('Environmental Data Dashboard'),
        dcc.Dropdown(
            id='page-dropdown',
            options=[
                {'label': 'Home', 'value': '/'},
                {'label': 'About', 'value': '/about'}
            ],
            value='/',
            clearable=False,
            style={'marginBottom': '20px'}
        ),
        html.Div(id='page-content')
    ])
])

# Home page layout
home_layout = html.Div([
    html.H2('Indoor Air Quality Dashboard'),
    html.P('''This dashboard presents environmental data collected by your device.
        You can specify a date range to visualize your data including
        particulate matter levels, temperature, humidity, AQI, and heat index.
    ''', className='text-center'),
    dcc.Dropdown(
        id='device-dropdown',
        options=[
    {'label': device[:-4], 'value': device[:-4]}
    for device in os.listdir(data_dir) if device.endswith('.csv')
    ],
    placeholder="Select a device"
    ),
    dcc.DatePickerRange(
        id='date-picker-range',
        start_date=None,
        end_date=None,
        start_date_placeholder_text="Start Date",
        end_date_placeholder_text="End Date"
    ),
    html.Div(id='average-output'),
    html.Div(className='graph-container', children=[
        dcc.Graph(id='pm-graph')
    ]),
    html.Div(className='graph-container', children=[
        dcc.Graph(id='temp-humidity-graph')
    ]),
    html.Div(className='graph-container', children=[
        dcc.Graph(id='aqi-graph')
    ]),
    html.Div(className='graph-container', children=[
        dcc.Graph(id='heat-index-graph')
    ])
])

# About page layout
about_layout = html.Div([
    html.H2('About This Dashboard', className='text-center', style={'marginBottom': '20px'}),
    html.P('''This dashboard collects and presents various environmental data, including:''', className='text-center'),
    html.Ul([
        html.Li('Particulate Matter levels (PM1.0, PM2.5, PM10)'),
        html.Li('Temperature and Humidity'),
        html.Li('Air Quality Index (AQI)'),
        html.Li('Heat Index')
    ], className='text-center'),
    html.P('For more information on air quality in NYC, please visit the following resources:', className='text-center'),
    html.Ul([
        html.Li(html.A('NYC Air Quality Data', href='https://www.nyc.gov/site/doh/health/health-topics/air-quality.page', target='_blank')),
        html.Li(html.A('EPA Air Quality Resources', href='https://www.epa.gov/air-trends', target='_blank'))
    ], className='text-center'),
    html.P('If you have any questions or need further information, please contact us.', className='text-center')
])

# Callback to update the page content based on the URL
@app.callback(Output('page-content', 'children'), [Input('page-dropdown', 'value')])
def display_page(value):
    if value == '/about':
        return about_layout
    else:
        return home_layout

# Update graphs and averages based on the selected device and date range
@app.callback(
    [Output('pm-graph', 'figure'),
     Output('temp-humidity-graph', 'figure'),
     Output('aqi-graph', 'figure'),
     Output('heat-index-graph', 'figure'),
     Output('average-output', 'children')],
    [Input('device-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date')]
)
def update_graphs(selected_device, start_date, end_date):
    if selected_device is None or start_date is None or end_date is None:
        return {}, {}, {}, {}, ""

    # Convert start_date and end_date to datetime
    start_date = pd.to_datetime(start_date).tz_localize('UTC')
    end_date = pd.to_datetime(end_date).tz_localize('UTC')

    data = load_data(data_dir, selected_device)

    if 'time' not in data.columns:
        return {}, {}, {}, {}, "No data available for the selected range."

    # Filter data using datetime comparisons
    data = data[(data['time'] >= start_date) & (data['time'] <= end_date)]

    if data.empty:
        return {}, {}, {}, {}, "No data available for the selected range."

    outdoor_data = load_data(data_dir, '88439')
    outdoor_data = outdoor_data[(outdoor_data['time'] >= start_date) & (outdoor_data['time'] <= end_date)]

    # Calculate averages and create graphs as before
    avg_pm25 = data['pm.2.5'].mean()
    avg_tempF = data['tempF'].mean()
    avg_humid = data['rh'].mean()
    avg_aqi = data['aqi'].mean()
    avg_heat_index = data.apply(lambda row: calculate_heat_index(row['tempF'], row['rh']), axis=1).mean()

    average_output = (f"Average PM2.5: {avg_pm25:.2f} µg/m³, "
                      f"Average Temperature: {avg_tempF:.2f} °F, "
                      f"Average Humidity: {avg_humid:.2f} %, "
                      f"Average AQI: {avg_aqi:.2f}, "
                      f"Average Heat Index: {avg_heat_index:.2f} °F")
    

    # Graph generation (unchanged)
    pm_fig = go.Figure()
    pm_fig.add_trace(go.Scatter(x=data['time'], y=data['pm.2.5'], mode='lines', name='PM 2.5 (µg/m³)', connectgaps=True, line=dict(color='blue')))
    pm_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['pm.2.5'], mode='lines', name='Outdoor PM 2.5 (µg/m³)', connectgaps=True, line=dict(color='green')))
    pm_fig.update_layout(
        title='Particulate Matter Over Time',
        xaxis_title='Time', 
        yaxis_title='Particulate Matter (µg/m³)'
    )

    temp_humidity_fig = go.Figure()
    temp_humidity_fig.add_trace(go.Scatter(x=data['time'], y=data['tempF'], mode='lines', name='Temperature (°F)', yaxis='y1', connectgaps=True, line=dict(color='blue')))
    temp_humidity_fig.add_trace(go.Scatter(x=data['time'], y=data['rh'], mode='lines', name='Humidity (%)', yaxis='y2', connectgaps=True, line=dict(color='red')))
    temp_humidity_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['tempF'], mode='lines', name='Outdoor Temperature (°F)', yaxis='y1', connectgaps=True, line=dict(color='green')))
    temp_humidity_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['rh'], mode='lines', name='Outdoor Humidity (%)', yaxis='y2', connectgaps=True, line=dict(color='purple')))
    temp_humidity_fig.update_layout(
        title='Temperature and Humidity Over Time',
        xaxis=dict(title='Time'),
        yaxis=dict(title='Temperature (°F)', side='left', showgrid=False),
        yaxis2=dict(title='Humidity (%)', side='right', overlaying='y', showgrid=False)
    )

    aqi_fig = go.Figure()
    aqi_fig.add_trace(go.Scatter(x=data['time'], y=data['aqi'], mode='lines', name='AQI'))
    aqi_fig.update_layout(
        title = 'Indoor Air Quality Index over Time',
        xaxis_title='Time', 
        yaxis_title='AQI'
    )

    data['heat_index'] = data.apply(lambda row: calculate_heat_index(row['tempF'], row['rh']), axis=1)
    outdoor_data['heat_index'] = outdoor_data.apply(lambda row: calculate_heat_index(row['tempF'], row['rh']), axis=1)
    heat_index_fig = go.Figure()
    heat_index_fig.add_trace(go.Scatter(x=data['time'], y=data['heat_index'], mode='lines', name='Heat Index (°F)', connectgaps=True, line=dict(color='red')))
    heat_index_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['heat_index'], mode='lines', name='Outdoor Heat Index (°F)', connectgaps=True, line=dict(color='blue')))
    heat_index_fig.update_layout(
        title='Heat Index Over Time',
        xaxis_title='Time', 
        yaxis_title='Heat Index (°F) '
    )

    return pm_fig, temp_humidity_fig, aqi_fig, heat_index_fig, average_output


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run_server(debug=True, host='0.0.0.0', port=port)
