import os
import pandas as pd
import re

# Define your input and output directories
input_dirs = {
    'mcci': 'C:\\Users\\Angy\\Documents\\iaq_ufd_nyc\\data_unprocessed\\mcci_unprocessed',
    'awair': 'C:\\Users\\Angy\\Documents\\iaq_ufd_nyc\\data_unprocessed\\awair_unprocessed',
    'purpleair': 'C:\\Users\\Angy\\Documents\\iaq_ufd_nyc\\data_unprocessed\\purpleair_unprocessed'
}
output_dir = 'C:\\Users\\Angy\\Documents\\iaq_ufd_nyc\\project\\data_processed'

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Function to convert temperature from Celsius to Fahrenheit
def celsius_to_fahrenheit(tempC):
    try:
        return tempC * 9/5 + 32
    except TypeError:
        print(f"Invalid temperature value: {tempC}")
        return None

# Function to convert time to Eastern Time
def convert_to_eastern_time(time_column):
    time_column = pd.to_datetime(time_column, errors='coerce')
    if time_column.dt.tz is None:
        return time_column.dt.tz_localize('UTC').dt.tz_convert('America/New_York')
    else:
        return time_column.dt.tz_convert('America/New_York')

# Function to standardize column names for Awair files
def standardize_awair_columns(df):
    # Check actual column names in the dataframe
    print(f"Original columns: {df.columns.tolist()}")
    column_mapping = {
        'timestamp(America/New_York)': 'time',
        'temp(°F)': 'tempF',  
        'humid': 'rh',
        'pm10': 'pm.10',
        'pm25': 'pm.2.5',
        'score': 'aqi'
    }
    df.rename(columns=column_mapping, inplace=True)
    print(f"Renamed columns: {df.columns.tolist()}")
    return df

# Function to standardize column names for purple air files
def standardize_purpleair_columns(df):
    # Check actual column names in the dataframe
    print(f"Original columns: {df.columns.tolist()}")
    column_mapping = {
        'time_stamp': 'time',
        'temperature': 'tempF',  
        'humidity': 'rh',
        'pm2.5_alt': 'pm.2.5',
    }
    df.rename(columns=column_mapping, inplace=True)
    print(f"Renamed columns: {df.columns.tolist()}")
    return df

# Dictionary to store data by device
device_data = {}

# Process MCCI files
for file in os.listdir(input_dirs['mcci']):
    if file.endswith('.csv'):
        file_path = os.path.join(input_dirs['mcci'], file)
        data = pd.read_csv(file_path)
        
        # Convert the temperature column to Fahrenheit if needed
        if 'tempC' in data.columns:
            data['tempF'] = data['tempC'].apply(celsius_to_fahrenheit)
            data.drop(columns=['tempC'], inplace=True)
        
        # Convert the time column to Eastern Time
        data['time'] = convert_to_eastern_time(data['time'])
        
        # Ensure there is a 'device' column in the data
        if 'device' not in data.columns:
            print(f"No 'device' column found in file: {file}")
            continue
        
        # Group data by device and append to the device_data dictionary
        for device, device_df in data.groupby('device'):
            if device not in device_data:
                device_data[device] = []
            device_data[device].append(device_df)

# Consolidate data for each device and save to CSV
for device, data_list in device_data.items():
    combined_data = pd.concat(data_list).drop_duplicates(subset=['time']).sort_values(by='time')
    
    # Check if the processed file for this device already exists
    output_file = os.path.join(output_dir, f'{device}.csv')
    if os.path.exists(output_file):
        existing_data = pd.read_csv(output_file)
        existing_data['time'] = pd.to_datetime(existing_data['time'], errors='coerce')
        combined_data = pd.concat([existing_data, combined_data]).drop_duplicates(subset=['time']).sort_values(by='time')
    
    # Save the combined data to the file
    combined_data.to_csv(output_file, index=False)
    print(f"Processed and updated MCCI file saved: {output_file}")

# Process purple air files
purple_files = {}
for file in os.listdir(input_dirs['purpleair']):
    if file.endswith('.csv'):
        file_path = os.path.join(input_dirs['purpleair'], file)
        base_name = '88439'
        
        if base_name not in purple_files:
            purple_files[base_name] = []
        
        data = pd.read_csv(file_path)
        
        # Standardize column names
        data = standardize_purpleair_columns(data)
      
        purple_files[base_name].append(data)

# Combine and save purple air data
for base_name, data_list in purple_files.items():
    combined_data = pd.concat(data_list).drop_duplicates(subset=['time']).sort_values(by='time')
    
    # Save the combined data to the file
    output_file = os.path.join(output_dir, f'{base_name}.csv')
    combined_data.to_csv(output_file, index=False)
    print(f"Processed and updated purple air file saved: {output_file}")

# Process Awair files
awair_files = {}
for file in os.listdir(input_dirs['awair']):
    if file.endswith('.csv'):
        file_path = os.path.join(input_dirs['awair'], file)
        base_name = re.sub(r'\(\d+\)', '', os.path.splitext(file)[0]).strip()
        
        if base_name not in awair_files:
            awair_files[base_name] = []
        
        data = pd.read_csv(file_path)
        
        # Standardize column names
        data = standardize_awair_columns(data)
        
        # Convert the time column to Eastern Time
        data['time'] = convert_to_eastern_time(data['time'])
        
        awair_files[base_name].append(data)

# Combine and save Awair data
for base_name, data_list in awair_files.items():
    combined_data = pd.concat(data_list).drop_duplicates(subset=['time']).sort_values(by='time')
    
    # Save the combined data to the file
    output_file = os.path.join(output_dir, f'{base_name}.csv')
    combined_data.to_csv(output_file, index=False)
    print(f"Processed and updated Awair file saved: {output_file}")

print("Processing complete. Files saved in:", output_dir)
