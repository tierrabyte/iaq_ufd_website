import os
import pandas as pd
import re
from dateutil import parser

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

# Function to attempt to fix and convert time to Eastern Time, handling each device type
def convert_to_eastern_time(time_column, device_type):
    """
    Convert the time column to Eastern Time. Handles timezone-awareness for various device types.
    """
    # Ensure the time_column is a Series and coerce to string for processing
    time_column = time_column.astype(str)  # Ensure all entries are strings
    try:
        if device_type == 'mcci':
            # Parse datetime; assume UTC
            time_column = pd.to_datetime(time_column, errors='coerce', utc=True)
            return time_column.dt.tz_convert('America/New_York')  # Convert to Eastern Time
        elif device_type in ['awair', 'purpleair']:
            # Assume timezone-naive or UTC
            time_column = pd.to_datetime(time_column, errors='coerce')
            if time_column.isna().all():
                raise ValueError("All entries in the time column failed to parse.")
            # Handle timezone localization
            if time_column.dt.tz is None:
                return time_column.dt.tz_localize('America/New_York', ambiguous='NaT', nonexistent='shift_forward')
            else:
                return time_column.dt.tz_convert('America/New_York')
        else:
            # Default case: Fallback for general datetime parsing
            time_column = pd.to_datetime(time_column, errors='coerce')
            return time_column.dt.tz_localize('America/New_York', ambiguous='NaT', nonexistent='shift_forward')
    except Exception as e:
        print(f"Error converting to Eastern Time for {device_type}: {e}")
        return pd.Series([pd.NaT] * len(time_column))  # Return NaT for all rows in case of failure


# Function to standardize column names for Awair files
def standardize_awair_columns(df):
    column_mapping = {
        'timestamp(America/New_York)': 'time',
        'temp(°F)': 'tempF',  
        'humid': 'rh',
        'pm10': 'pm.10',
        'pm25': 'pm.2.5',
        'score': 'aqi'
    }
    df.rename(columns=column_mapping, inplace=True)
    return df

# Function to standardize column names for PurpleAir files
def standardize_purpleair_columns(df):
    column_mapping = {
        'time_stamp': 'time',
        'temperature': 'tempF',  
        'humidity': 'rh',
        'pm2.5_alt': 'pm.2.5',
    }
    df.rename(columns=column_mapping, inplace=True)
    return df

# Dictionary to store data by device
device_data = {}

# Process MCCI files (assumed to be in UTC)
for file in os.listdir(input_dirs['mcci']):
    if file.endswith('.csv'):
        file_path = os.path.join(input_dirs['mcci'], file)
        data = pd.read_csv(file_path)
        
        # Convert the temperature column to Fahrenheit if needed
        if 'tempC' in data.columns:
            data['tempF'] = data['tempC'].apply(celsius_to_fahrenheit)
            data.drop(columns=['tempC'], inplace=True)
        
        # Convert the time column to Eastern Time from UTC
        data['time'] = convert_to_eastern_time(data['time'], 'mcci')
        
        # Filter out rows where 'time' is invalid (NaT)
        data = data[data['time'].notna()]
        
        # Ensure there is a 'device' column in the data
        if 'device' not in data.columns:
            print(f"No 'device' column found in file: {file}")
            continue
        
        # Group data by device and append to the device_data dictionary
        for device, device_df in data.groupby('device'):
            if device not in device_data:
                device_data[device] = []
            device_data[device].append(device_df)

# Consolidate data for each MCCI device and save to CSV
for device, data_list in device_data.items():
    combined_data = pd.concat(data_list).drop_duplicates(subset=['time']).sort_values(by='time')
    
    # Check if the processed file for this device already exists
    output_file = os.path.join(output_dir, f'{device}.csv')
    if os.path.exists(output_file):
        existing_data = pd.read_csv(output_file)
        existing_data['time'] = pd.to_datetime(existing_data['time'], errors='coerce',utc=True)
        combined_data = pd.concat([existing_data, combined_data]).drop_duplicates(subset=['time']).sort_values(by='time')
    
    # Save the combined data to the file
    combined_data.to_csv(output_file, index=False)
    print(f"Processed and updated MCCI file saved: {output_file}")

# Process PurpleAir files (includes timezone offset)
# Process PurpleAir files (includes timezone offset)
purple_files = {}
for file in os.listdir(input_dirs['purpleair']):
    if file.endswith('.csv'):
        file_path = os.path.join(input_dirs['purpleair'], file)
        base_name = '88439'  # Adjust this as needed
        
        if base_name not in purple_files:
            purple_files[base_name] = []
        
        data = pd.read_csv(file_path)
        
        # Standardize column names
        data = standardize_purpleair_columns(data)
        
        # Convert the time column to UTC
        data['time'] = pd.to_datetime(data['time'], errors='coerce', utc=True)
        
        # Debug invalid timestamps
        if data['time'].isna().any():
            print(f"Invalid timestamps found in file: {file_path}")
            print(data[data['time'].isna()])
        
        # Filter out rows where 'time' is invalid (NaT)
        data = data[data['time'].notna()]
        
        purple_files[base_name].append(data)

# Combine and save PurpleAir data
for base_name, data_list in purple_files.items():
    combined_data = pd.concat(data_list, ignore_index=True).drop_duplicates(subset=['time']).sort_values(by='time')
    
    # Path to the existing processed file
    output_file = os.path.join(output_dir, f'{base_name}.csv')
    
    if os.path.exists(output_file):
        # Read existing data and ensure proper datetime parsing
        existing_data = pd.read_csv(output_file)
        existing_data['time'] = pd.to_datetime(existing_data['time'], errors='coerce', utc=True)
        
        # Debug existing data range
        print(f"Existing data range for {base_name}: {existing_data['time'].min()} to {existing_data['time'].max()}")
        
        # Concatenate with new data
        combined_data = pd.concat([existing_data, combined_data], ignore_index=True)
        combined_data = combined_data.drop_duplicates(subset=['time']).sort_values(by='time')
    
    # Debug the combined data range
    print(f"Saving data for {base_name}.")
    print(f"Combined data range: {combined_data['time'].min()} to {combined_data['time'].max()}")
    
    # Save to file
    combined_data.to_csv(output_file, index=False)
    print(f"Processed and updated PurpleAir file saved: {output_file}")


print("Processing complete. Files saved in:", output_dir)
