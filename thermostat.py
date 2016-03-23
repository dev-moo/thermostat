#!/usr/bin/env python

import sys
import socket
import json
from time import sleep, gmtime, strftime
import datetime 
import select
import threading

sys.path.insert(0, '/var/scripts/thermostat')

import get_temp
import pid_control


ac_server_address = ('192.168.1.6', 10000)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.setblocking(0)


class AC_Settings(object):

	def __init__(self):
		self.init = False
		self.power = None
		self.mode = None
		self.fan = None
		self.temp = None
		self.TTL = 0

		
		
def log_event(e):

	tstamp = strftime("%Y%m%d%H%M%S")
	
	print e
	
	f = open('/var/scripts/thermostat/temp_controller_log.csv', 'a')
	f.write('"' + str(tstamp) + '","' + str(e) + '"\n')
	f.close()	
	

def get_ac_settings(cur_settings):
	
	for i in xrange(1, 50):
		
		try: 
			
			log_event("Getting settings from A/C") 
			
			sent = sock.sendto(json.dumps({'Operation': 'GET', 'Type': 'Settings'}), ac_server_address)
				
			ready = select.select([sock], [], [], 20)	
				
			if ready[0]:
				data = sock.recv(4096)
				data = json.loads(data)
								
				cur_settings.power = data['Power']
				cur_settings.mode = data['Mode']
				cur_settings.fan = data['Fan']
				cur_settings.temp = data['Temp']
				cur_settings.init = True
				cur_settings.TTL = 10
				
				log_event("Retrieved settings from A/C") 
				
				return cur_settings
			
		except:
			print "Unable to connect to A/C, trying again..."
		
		sleep(i*i)
	
	return None
	



def control_ac(command):
	
	command = json.dumps(command)
	
	try:
		
		log_event("Sending command: " + str(command))
	
		sent = sock.sendto(command, ac_server_address)
		
		print >>sys.stderr, 'sent %s bytes back to %s' % (sent, ac_server_address)
			
	except:
		log_event("Error sending command to A/C")
		
	return True

	

def check_settings(current_settings, desired_settings):

	if desired_settings.power and current_settings.power != desired_settings.power:
		log_event("Turning A/C " + desired_settings.power)
		control_ac({'Operation': 'SET', 'Type': 'Power', 'Value': desired_settings.power})
		current_settings = get_ac_settings(current_settings)

		if desired_settings.power == 'Off':
			return current_settings
		
	if desired_settings.mode and current_settings.mode != desired_settings.mode:
		log_event("Changing A/C to " + desired_settings.mode + " mode")
		control_ac({'Operation': 'SET', 'Type': 'Mode', 'Value': desired_settings.mode})
		current_settings = get_ac_settings(current_settings)
		
		if desired_settings.mode == 'Fan':
			return current_settings
	
	#log_event("Desired temp: " + str(desired_settings.temp) + " Current temp: " + str(current_settings.temp))
	
	if desired_settings.temp and current_settings.temp != desired_settings.temp:
		log_event("Turning A/C " + str(desired_settings.temp))
		control_ac({'Operation': 'SET', 'Type': 'Temp', 'Value': str(desired_settings.temp)})
		current_settings = get_ac_settings(current_settings)		
	
	return current_settings
		

def thermostat(e, target_temp):

	log_event("Starting temp control...")
	
	pid = pid_control.PID_Controller(target_temp, get_temp.get_room_temp())
	
	current_settings = AC_Settings()
	current_settings = get_ac_settings(current_settings)
	
	while True:
	
		startTime = datetime.datetime.now()
						
		desired_settings = AC_Settings()
			
		room_temp = get_temp.get_room_temp()
		
		log_event("Current room temp is " + str(room_temp) + " degrees")
		
		error = target_temp - room_temp
		
		log_event("Target room temp is " + str(target_temp) + " degrees")
		log_event('Error: ' + str(error))
	
		pid.update(room_temp)
		
		log_event('PID Output: ' + str(pid.Output))
		
		
		if int(pid.Output) < 22:
			desired_settings.power = 'On'
			desired_settings.mode = 'Cool'				
			desired_settings.temp = '22'
			
		elif int(pid.Output) >= 22 and int(pid.Output) <= 30:
			desired_settings.power = 'On'
			desired_settings.mode = 'Cool'			
			desired_settings.temp = str(int(pid.Output))
			
		elif int(pid.Output) > 30 and pid.Output <= 33:
			desired_settings.power = 'On'
			desired_settings.mode = 'Fan'
			desired_settings.temp = '30'
			
		#elif pid.Output > 33:
		else:
			desired_settings.power = 'Off'
		
		
		current_settings = check_settings(current_settings, desired_settings)
	

		for i in xrange(1, 60):
			sleep(1)
			
			if e.isSet():
				log_event("Temp control thread has been stopped")
				exit()
			
			tc = datetime.datetime.now() - startTime
			tc = tc.total_seconds()
			
			if tc > 61:
				break
		

		current_settings.TTL -= 1
		
		if current_settings.TTL <= 0:
			current_settings = get_ac_settings(current_settings)
			
		
		log_event("Change in room temp is " + str(get_temp.get_room_temp() - room_temp) + " degrees")
		
		timeChange = datetime.datetime.now() - startTime
		timeChange = timeChange.total_seconds()
		log_event("Number of seconds to complete this cycle: " + str(timeChange))
		log_event("Current settings TTL: " + str(current_settings.TTL))
		
		log_event('')
		
		desired_settings = None
		
		

if __name__ == "__main__":

	thermostat(27)
