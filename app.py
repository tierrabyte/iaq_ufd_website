import os
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pytz

# Resolve base path relative to this file
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data_processed')

# Initialize the Dash app with a white theme template
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Environmental Data Dashboard"
server = app.server

# Load data safely without timezone conversion (already handled externally)
def get_device_files():
    try:
        return sorted([f for f in os.listdir(data_dir) if f.endswith('.csv') and not f.startswith('88439')])
    except Exception as e:
        print(f"[ERROR] Cannot list data directory: {e}")
        return []

def load_data(directory, device):
    try:
        file_path = os.path.join(directory, f'{device}.csv')
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['time'] = pd.to_datetime(df['time'], errors='coerce', utc=True).dt.tz_convert('America/New_York')
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

def get_device_options():
    return [{'label': f[:-4], 'value': f[:-4]} for f in get_device_files()]

def get_pm25_aqi_category(avg_pm):
    if avg_pm <= 12.0:
        return "🟢 Good (0–12 µg/m³)", "green"
    elif avg_pm <= 35.4:
        return "🟡 Moderate (12.1–35.4 µg/m³)", "yellow"
    elif avg_pm <= 55.4:
        return "🟠 Unhealthy for Sensitive Groups (35.5–55.4 µg/m³)", "orange"
    elif avg_pm <= 150.4:
        return "🔴 Unhealthy (55.5–150.4 µg/m³)", "red"
    elif avg_pm <= 250.4:
        return "🔷 Very Unhealthy (150.5–250.4 µg/m³)", "purple"
    else:
        return "🔵 Hazardous (250.5+ µg/m³)", "maroon"

# Layout
app.layout = html.Div([
    html.H1('Environmental Data Dashboard'),
    dcc.Dropdown(id='device-dropdown', options=get_device_options(), placeholder="Select a device"),
    dcc.DatePickerRange(id='date-picker-range'),
    dcc.Dropdown(
        id='metric-selector',
        options=[
            {'label': 'Summary', 'value': 'summary'},
            {'label': 'PM2.5', 'value': 'pm.2.5'},
            {'label': 'Temperature', 'value': 'tempF'},
            {'label': 'Humidity', 'value': 'rh'},
            {'label': 'AQI', 'value': 'aqi'},
            {'label': 'Heat Index', 'value': 'heat_index'}
        ],
        value='summary',
        style={'marginBottom': '20px'}
    ),
    html.Div(id='dynamic-content')
])

@app.callback(
    Output('dynamic-content', 'children'),
    [Input('device-dropdown', 'value'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('metric-selector', 'value')]
)
def render_dynamic_content(device, start_date, end_date, metric):
    if not device or not start_date or not end_date:
        return html.Div("Please select a device and date range.")

    df = load_data(data_dir, device)
    outdoor_df = load_data(data_dir, '88439')

    start_date = pd.to_datetime(start_date).tz_localize('America/New_York')
    end_date = pd.to_datetime(end_date).tz_localize('America/New_York')

    df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
    outdoor_df = outdoor_df[(outdoor_df['time'] >= start_date) & (outdoor_df['time'] <= end_date)]

    if df.empty:
        return html.Div("No data available for the selected range.")

    df['heat_index'] = df.apply(lambda row: calculate_heat_index(row['tempF'], row['rh']), axis=1)
    outdoor_df['heat_index'] = outdoor_df.apply(lambda row: calculate_heat_index(row['tempF'], row['rh']), axis=1)

    if metric == 'summary':
        avg_pm = df['pm.2.5'].mean()
        category_label, color = get_pm25_aqi_category(avg_pm)

        df['date'] = df['time'].dt.date
        daily_avg = df.groupby('date')[['pm.2.5', 'tempF', 'rh', 'aqi', 'heat_index']].mean().reset_index()

        peak_hour = df.groupby(df['time'].dt.hour)['pm.2.5'].mean().idxmax()

        summary_text = [
            html.H3("Summary Report"),
            html.Div(f"Air Quality Status: {category_label}", style={'color': color, 'fontWeight': 'bold'}),
            html.P(f"Average PM2.5: {avg_pm:.2f} µg/m³"),
            html.P(f"Max PM2.5: {df['pm.2.5'].max():.2f} µg/m³"),
            html.P(f"Min PM2.5: {df['pm.2.5'].min():.2f} µg/m³"),
            html.P(f"Peak PM2.5 Hour: {peak_hour}:00"),
            html.P(f"Average Temperature: {df['tempF'].mean():.2f} °F"),
            html.P(f"Average Humidity: {df['rh'].mean():.2f} %"),
            html.P(f"Average AQI: {df['aqi'].mean():.2f}"),
            html.P(f"Average Heat Index: {df['heat_index'].mean():.2f} °F"),
            html.H4("Daily Averages:"),
            dcc.Graph(
                figure=go.Figure(
                    data=[go.Scatter(x=daily_avg['date'], y=daily_avg[col], mode='lines+markers', name=col)
                          for col in ['pm.2.5', 'tempF', 'rh', 'aqi', 'heat_index']],
                    layout=go.Layout(
                        title="Daily Average Environmental Metrics",
                        xaxis_title="Date",
                        yaxis_title="Value",
                        template='plotly_white'
                    )
                )
            )
        ]
        return html.Div(summary_text)

    elif metric in df.columns:
        df['hour'] = df['time'].dt.hour
        outdoor_df['hour'] = outdoor_df['time'].dt.hour
        hourly_avg = df.groupby('hour')[metric].mean().reset_index()
        outdoor_hourly = outdoor_df.groupby('hour')[metric].mean().reset_index()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['time'], y=df[metric], mode='lines', name=f"{device} {metric}"))
        fig.add_trace(go.Scatter(x=outdoor_df['time'], y=outdoor_df[metric], mode='lines', name="Outdoor 88439"))
        fig.update_layout(title=f"{metric} Over Time", xaxis_title="Time", yaxis_title=metric, template='plotly_white')

        trace_fig = go.Figure()
        trace_fig.add_trace(go.Scatter(x=hourly_avg['hour'], y=hourly_avg[metric], mode='lines+markers', name=f'{device} Avg {metric}'))
        trace_fig.add_trace(go.Scatter(x=outdoor_hourly['hour'], y=outdoor_hourly[metric], mode='lines+markers', name='Outdoor Avg'))
        trace_fig.update_layout(title=f"Hourly Average {metric}", xaxis_title="Hour of Day", yaxis_title=f"Average {metric}", template='plotly_white')

        return html.Div([
            dcc.Graph(figure=fig),
            dcc.Graph(figure=trace_fig)
        ])

    return html.Div("Invalid metric selected.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run_server(debug=False, host="0.0.0.0", port=port)
