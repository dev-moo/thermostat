#!/usr/bin/env python

import re

def get_room_temp():
	
	probeFile = '/sys/bus/w1/devices/28-000007662891/w1_slave'

	file = open(probeFile, 'r')

	probedata = file.readlines()
	probedata = probedata[1]

	extract = re.search('t=(.+?)\n', probedata)

	temp = extract.group(1)

	return float(temp)/1000


if __name__ == "__main__":

	print get_room_temp()

