# script to download InfluxDB json data and convert to csv format
# assumes the script get-influxdb-data.ccny.sh is in the same directory


# edit as needed, then run by  >> python InfluxDBjson2csv.py

import numpy as np
import os
import json

# ---- User Input Section  -----#
data_folder = '/home/student/data/'
code_folder = '/home/student/code/'
# if you prefer to automatically use the current folder:
#data_folder = os.get_cwd()

json_file = 'october_07_october_21.json'
csv_file = 'october_07_october_21.csv'

timelapse = '0'  # days to get data before current time, set to 0 for range
time1 = '2024-10-07T00:00:00Z'
time2 = '2024-10-21T23:59:59Z'

username = 'brian'
password = 'prathap'
#---------------------------------#

# download the data
if (int(timelapse) != 0):
	command = code_folder+'get-influxdb-data-ccny.sh -u '+username+':'+password + ' -v -t'+timelapse+ ' > ' + data_folder + json_file
else:
	command = code_folder+'get-influxdb-data-ccny.sh -u '+username+':'+password + ' -v -w "time >= \''+time1+ '\' AND time <\''+time2+'\'" > '+data_folder+json_file

print(command)
os.system(command)

# convert json file into list of dicts, pull out headers and make csv row
fid = open(data_folder+json_file,'r')
data_struct = json.load(fid)
fid.close()

headers = data_struct['results'][0]['series'][0]['columns']
headerline = 'device,'
nvars = len(headers)
for v in range(0,nvars):
	headerline = headerline + headers[v]+','
headerline = headerline + '\n'

fid = open(data_folder+csv_file,'w')
fid.write(headerline)

# find number of devices, then cycle through
ndev = len(data_struct['results'][0]['series'])

for dev in range(0,ndev):

	device = data_struct['results'][0]['series'][dev]['tags']['devID']

	# now cycle through data for each device, adding to the csv file
	data = data_struct['results'][0]['series'][dev]['values']
	ndat = len(data)
	for d in range(0,ndat):
		datline = device+','
		for v in range(0,nvars):
			datline = datline + str(data[d][v]) +','
		datline = datline + '\n'
		fid.write(datline)

fid.close()
