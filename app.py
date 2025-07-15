import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

# Resolve base path relative to this file
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data_processed')

# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Environmental Data Dashboard"
server = app.server

# Helper to safely list available devices
def get_device_files():
    try:
        return sorted([f for f in os.listdir(data_dir) if f.endswith('.csv')])
    except Exception as e:
        print(f"[ERROR] Cannot list data directory: {e}")
        return []

def load_data(directory, device):
    try:
        file_path = os.path.join(directory, f'{device}.csv')
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['time'] = pd.to_datetime(df['time'], errors='coerce')
            df = df[df['time'].notna()]
            return df
    except Exception as e:
        print(f"[WARN] Failed to load device {device}: {e}")
    return pd.DataFrame()

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
    if temp_f < 80 or rh < 40:
        heat_index = 0.5 * (temp_f + 61.0 + ((temp_f - 68.0) * 1.2) + (rh * 0.094))
    elif rh < 13 and 80 <= temp_f <= 112:
        adjustment = ((13 - rh) / 4) * ((17 - abs(temp_f - 95)) / 17) ** 0.5
        heat_index -= adjustment
    elif rh > 85 and 80 <= temp_f <= 87:
        adjustment = ((rh - 85) / 10) * ((87 - temp_f) / 5)
        heat_index += adjustment
    return heat_index

# Dynamic device dropdown options
def get_device_options():
    return [{'label': f[:-4], 'value': f[:-4]} for f in get_device_files()]

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(className='container', children=[
        html.H1('Environmental Data Dashboard'),
        dcc.Dropdown(
            id='page-dropdown',
            options=[{'label': 'Home', 'value': '/'}, {'label': 'About', 'value': '/about'}],
            value='/', clearable=False, style={'marginBottom': '20px'}
        ),
        html.Div(id='page-content')
    ])
])

home_layout = html.Div([
    html.H2('Indoor Air Quality Dashboard'),
    html.P('This dashboard presents environmental data collected by your device.'),
    dcc.Dropdown(
        id='device-dropdown',
        options=get_device_options(),
        placeholder="Select a device"
    ),
    dcc.DatePickerRange(
        id='date-picker-range',
        start_date=None, end_date=None,
        start_date_placeholder_text="Start Date",
        end_date_placeholder_text="End Date"
    ),
    html.Div(id='average-output'),
    html.Div([
        html.H3("Particulate Matter Over Time"),
        dcc.Graph(id='pm-graph')
    ]),
    html.Div([
        html.H3("Temperature and Humidity Over Time"),
        dcc.Graph(id='temp-humidity-graph')
    ]),
    html.Div([
        html.H3("Air Quality Index Over Time"),
        dcc.Graph(id='aqi-graph')
    ]),
    html.Div([
        html.H3("Heat Index Over Time"),
        dcc.Graph(id='heat-index-graph')
    ])
])

about_layout = html.Div([
    html.H2('About This Dashboard'),
    html.P('This dashboard collects and presents various environmental data:'),
    html.Ul([
        html.Li('Particulate Matter levels (PM1.0, PM2.5, PM10)'),
        html.Li('Temperature and Humidity'),
        html.Li('Air Quality Index (AQI)'),
        html.Li('Heat Index')
    ]),
    html.P('NYC Air Resources:'),
    html.Ul([
        html.Li(html.A('NYC Air Quality Data', href='https://www.nyc.gov/site/doh/health/health-topics/air-quality.page', target='_blank')),
        html.Li(html.A('EPA Air Quality Resources', href='https://www.epa.gov/air-trends', target='_blank'))
    ])
])

@app.callback(Output('page-content', 'children'), [Input('page-dropdown', 'value')])
def display_page(value):
    return about_layout if value == '/about' else home_layout

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
    if not selected_device or not start_date or not end_date:
        return {}, {}, {}, {}, ""

    start_date = pd.to_datetime(start_date).tz_localize('UTC')
    end_date = pd.to_datetime(end_date).tz_localize('UTC')

    data = load_data(data_dir, selected_device)
    if 'time' not in data.columns:
        return {}, {}, {}, {}, "No data available."
    
    data = data[(data['time'] >= start_date) & (data['time'] <= end_date)]
    if data.empty:
        return {}, {}, {}, {}, "No data for selected range."

    outdoor_data = load_data(data_dir, '88439')
    outdoor_data = outdoor_data[(outdoor_data['time'] >= start_date) & (outdoor_data['time'] <= end_date)]

    avg_pm25 = data['pm.2.5'].mean()
    avg_tempF = data['tempF'].mean()
    avg_humid = data['rh'].mean()
    avg_aqi = data['aqi'].mean()
    avg_heat_index = data.apply(lambda row: calculate_heat_index(row['tempF'], row['rh']), axis=1).mean()

    avg_output = (f"Average PM2.5: {avg_pm25:.2f} µg/m³, "
                  f"Temp: {avg_tempF:.2f} °F, "
                  f"Humidity: {avg_humid:.2f} %, "
                  f"AQI: {avg_aqi:.2f}, "
                  f"Heat Index: {avg_heat_index:.2f} °F")

    pm_fig = go.Figure()
    pm_fig.add_trace(go.Scatter(x=data['time'], y=data['pm.2.5'], mode='lines', name='Indoor PM2.5'))
    pm_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['pm.2.5'], mode='lines', name='Outdoor PM2.5'))
    pm_fig.update_layout(title='Particulate Matter Over Time')

    temp_humidity_fig = go.Figure()
    temp_humidity_fig.add_trace(go.Scatter(x=data['time'], y=data['tempF'], mode='lines', name='Indoor Temp'))
    temp_humidity_fig.add_trace(go.Scatter(x=data['time'], y=data['rh'], mode='lines', name='Indoor RH', yaxis='y2'))
    temp_humidity_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['tempF'], mode='lines', name='Outdoor Temp'))
    temp_humidity_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['rh'], mode='lines', name='Outdoor RH', yaxis='y2'))
    temp_humidity_fig.update_layout(
        title='Temperature and Humidity Over Time',
        yaxis=dict(title='Temperature (°F)'),
        yaxis2=dict(title='Humidity (%)', overlaying='y', side='right')
    )

    aqi_fig = go.Figure()
    aqi_fig.add_trace(go.Scatter(x=data['time'], y=data['aqi'], mode='lines', name='Indoor AQI'))
    aqi_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['aqi'], mode='lines', name='Outdoor AQI'))
    aqi_fig.update_layout(
        title='Air Quality Index Over Time',
        xaxis_title='Time',
        yaxis_title='AQI',
        showlegend=True
    )

    data['heat_index'] = data.apply(lambda row: calculate_heat_index(row['tempF'], row['rh']), axis=1)
    outdoor_data['heat_index'] = outdoor_data.apply(lambda row: calculate_heat_index(row['tempF'], row['rh']), axis=1)
    heat_fig = go.Figure()
    heat_fig.add_trace(go.Scatter(x=data['time'], y=data['heat_index'], mode='lines', name='Indoor Heat Index'))
    heat_fig.add_trace(go.Scatter(x=outdoor_data['time'], y=outdoor_data['heat_index'], mode='lines', name='Outdoor Heat Index'))
    heat_fig.update_layout(
        title='Heat Index Over Time',
        xaxis_title='Time',
        yaxis_title='Heat Index (°F)',
        showlegend=True
    )

    return pm_fig, temp_humidity_fig, aqi_fig, heat_fig, avg_output

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run_server(debug=False, host='0.0.0.0', port=port)
