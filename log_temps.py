#!/usr/bin/env python

from time import gmtime, strftime
import get_temp


room_temp = get_temp.get_room_temp()

date = strftime("%Y-%m-%d")
time = strftime("%H:%M:%S")
tstamp = strftime("%Y%m%d%H%M%S")


output = '"' + str(date) + '","' + str(time) + '","' + str(tstamp) + '","' + str(room_temp) + '"'

print output

#Open file for output
f = open('/var/scripts/thermostat/temperature_log.csv', 'a')
f.write(output + '\n')
f.close()
