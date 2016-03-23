#!/usr/bin/env python

#add a comment to this file

import socket
import sys
import threading
import json
from time import sleep

sys.path.insert(0, '/var/scripts/thermostat') 

import get_temp
import thermostat

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Bind the socket to the port
server_address = ('192.168.1.3', 10001)
print >>sys.stderr, 'starting up on %s port %s' % server_address

while True:
	
	try: 
		sock.bind(server_address)
		break

	except:
		print 'Socket bind failed, trying again...'
		sleep(5)
		
	
target_temp = 25
		
def start_climate_control(s, temp):
	
	if climate_control_status() == 'TRUE':
		print 'Thread already active'
		return False
		
	s.clear()
	t = threading.Thread(name='thermostat', target=thermostat.thermostat, args=(s, temp))
	t.start()	

def stop_climate_control(s):
	
	s.set()
	
	for i in xrange(1, 60):
		
		if climate_control_status() == 'FALSE':
			return True
		
		sleep(1)
		
	return False	
	

def climate_control_status():
	for t in threading.enumerate():
		if t.getName() == 'thermostat':
			return 'TRUE'
			
	return 'FALSE'

stop = threading.Event()


if __name__ == "__main__":

			
	while True:
		
		print >>sys.stderr, '\nwaiting to receive message'
		data, address = sock.recvfrom(4096)

		print >>sys.stderr, 'received %s bytes from %s' % (len(data), address)
		print >>sys.stderr, data

		
		if data:
			try:
				command = json.loads(data)
				
				print command
				
				if command['OP'] == "START":
					print "Start command"
					target_temp = float(command['TEMP'])
					print "Temp: " + str(target_temp)
					start_climate_control(stop, target_temp)
					print "Started"
				
				if command['OP'] == "STOP":
					stop_climate_control(stop)				
				
				if command['OP'] == "STATUS":
					climate_control_status()
					
					d = {'ACTIVE': str(climate_control_status()), 'TARGETTEMP': str(target_temp), 'ROOMTEMP': str(get_temp.get_room_temp())}
										
					sent = sock.sendto(json.dumps(d), address)	
					print json.dumps(d)
					print >>sys.stderr, 'sent %s bytes back to %s' % (sent, address)
				
			except:
				print "Error"
				
	
