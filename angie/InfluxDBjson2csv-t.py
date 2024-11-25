# script to download InfluxDB json data and convert to csv format
# assumes the script get-influxdb-data.ccny.sh is in the same directory


# edit as needed, then run by  >> python InfluxDBjson2csv.py

import numpy as np
import os
import json

# ---- User Input Section  -----#
#data_folder = '/users/brianvanthull2/desktop/TTNdata'
# if you prefer to automatically use the current folder:
data_folder = os.getcwd()
code_folder = data_folder

json_file = 'newdata.json'
csv_file = 'newdata.csv'

timelapse = '1d'  # days or hours to get data before current time, set to '0' for range
time1 = '2024-08-01T04:00:00Z'
time2 = '2020-08-07T10:00:00Z'

username = 'brian'
password = 'prathap'
#---------------------------------#

# download the data
if (timelapse != '0'):
	deltaT = timelapse[0:-1]
	Ttype = timelapse[-1]
	command = code_folder+'/get-influxdb-data-ccny-'+Ttype+'.sh -u '+username+':'+password + ' -v -t'+deltaT+ ' > ' + data_folder +'/'+ json_file
else:
	command = code_folder+'/get-influxdb-data-ccny.sh -u '+username+':'+password + ' -v -w "time >= \''+time1+ '\' AND time <\''+time2+'\'" > '+data_folder+'/'+json_file

print(command)
os.system(command)

# convert json file into list of dicts, pull out headers and make csv row
fid = open(data_folder+'\\'+json_file,'r')
data_struct = json.load(fid)
fid.close()

headers = data_struct['results'][0]['series'][0]['columns']
headerline = 'device,'
nvars = len(headers)
for v in range(0,nvars):
	headerline = headerline + headers[v]+','
headerline = headerline + '\n'

fid = open(data_folder+'/'+csv_file,'w')
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
