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

#Constants
HEATING_MIN_TEMP = 16
HEATING_MAX_TEMP = 21

COOLING_MIN_TEMP = 23
COOLING_MAX_TEMP = 30

PID_OVERRUN = 4


#Class to store settings
class AC_Settings(object):

	def __init__(self):
		self.init = False
		self.power = None
		self.mode = None
		self.fan = None
		self.temp = None
		self.TTL = 0

		
#Log events to text file		
def log_event(e):

	tstamp = strftime("%Y%m%d%H%M%S")
	
	print e
	
	f = open('/var/scripts/thermostat/temp_controller_log.csv', 'a')
	f.write('"' + str(tstamp) + '","' + str(e) + '"\n')
	f.close()	
	
	
#Connect to A/C server and probe for current settings
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
	


#Connect to A/C server and change a setting
def control_ac(command):
	
	command = json.dumps(command)
	
	try:
		
		log_event("Sending command: " + str(command))
	
		sent = sock.sendto(command, ac_server_address)
		
		print >>sys.stderr, 'sent %s bytes back to %s' % (sent, ac_server_address)
			
	except:
		log_event("Error sending command to A/C")
		
	return True

	
#Check for difference between current settings a desired settings
#Set A/C to the desired setting if differences are found
def apply_settings(current_settings, desired_settings):

	#Check Power
	if desired_settings.power and current_settings.power != desired_settings.power:
		log_event("Turning A/C " + desired_settings.power)
		control_ac({'Operation': 'SET', 'Type': 'Power', 'Value': desired_settings.power})
		current_settings = get_ac_settings(current_settings)

		if desired_settings.power == 'Off':
			return current_settings
	
	#Check mode (fan, cool, heat)
	if desired_settings.mode and current_settings.mode != desired_settings.mode:
		log_event("Changing A/C to " + desired_settings.mode + " mode")
		control_ac({'Operation': 'SET', 'Type': 'Mode', 'Value': desired_settings.mode})
		current_settings = get_ac_settings(current_settings)
		
		if desired_settings.mode == 'Fan':
			return current_settings
	
	#log_event("Desired temp: " + str(desired_settings.temp) + " Current temp: " + str(current_settings.temp))
	
	#Check temperature
	if desired_settings.temp and current_settings.temp != desired_settings.temp:
		log_event("Turning A/C " + str(desired_settings.temp))
		control_ac({'Operation': 'SET', 'Type': 'Temp', 'Value': str(desired_settings.temp)})
		current_settings = get_ac_settings(current_settings)		
	
	return current_settings


#Produce desired output settings from the output of the PID controller	
def calculate_desired_settings(desired_settings, control_mode, pid_output):
	
		
	if control_mode == 'heating':
	
		if pid_output < HEATING_MIN_TEMP-PID_OVERRUN:
			desired_settings.power = 'Off'
		
		elif pid_output >= HEATING_MIN_TEMP-PID_OVERRUN and pid_output < HEATING_MIN_TEMP:
			desired_settings.power = 'On'
			desired_settings.mode = 'Heat'			
			desired_settings.temp = str(HEATING_MIN_TEMP)			
			
		elif pid_output >= HEATING_MIN_TEMP and pid_output <= HEATING_MAX_TEMP:
			desired_settings.power = 'On'
			desired_settings.mode = 'Heat'			
			desired_settings.temp = str(pid_output)
			
		elif pid_output > HEATING_MAX_TEMP:
			desired_settings.power = 'On'
			desired_settings.mode = 'Heat'			
			desired_settings.temp = str(HEATING_MAX_TEMP)
		
	
	elif control_mode == 'cooling':
	
		if pid_output < COOLING_MIN_TEMP:
			desired_settings.power = 'On'
			desired_settings.mode = 'Cool'				
			desired_settings.temp = str(COOLING_MIN_TEMP)
			
		elif pid_output >= COOLING_MIN_TEMP and pid_output <= COOLING_MAX_TEMP:
			desired_settings.power = 'On'
			desired_settings.mode = 'Cool'			
			desired_settings.temp = str(pid_output)
			
		elif pid_output > COOLING_MAX_TEMP and pid_output < COOLING_MAX_TEMP + PID_OVERRUN:
			desired_settings.power = 'On'
			desired_settings.mode = 'Fan'
			desired_settings.temp = str(COOLING_MAX_TEMP)

		else:
			desired_settings.power = 'Off'		

			
	return None
			
	
#Main loop
def thermostat(e, target_temp, control_mode):

	log_event("Starting temp control...")
	log_event("Control Mode: " + control_mode)
	
	#Instantiate PID Controller
	pid = pid_control.PID_Controller(target_temp, get_temp.get_room_temp(), min_temp - PID_OVERRUN, max_temp + PID_OVERRUN)
	
	#Get current setting from the A/C
	current_settings = AC_Settings()
	current_settings = get_ac_settings(current_settings)
	
	#Loop
	while True:
	
		startTime = datetime.datetime.now() #For logging purposes
						
		desired_settings = AC_Settings() 	#Place to store desired setting of A/C
			
		room_temp = get_temp.get_room_temp()	#Get current room temperature
		
		log_event("Current room temp is " + str(room_temp) + " degrees")
		
		error = target_temp - room_temp	#Calculate error
		
		log_event("Target room temp is " + str(target_temp) + " degrees")
		log_event('Error: ' + str(error))
	
		pid.update(room_temp)	#Calculate new output from PID Controller
		
		log_event('PID Output: ' + str(pid.Output))
		
		desired_settings = calculate_desired_settings(desired_settings, control_mode, int(pid.output))	#Get new settings to apply to A/C
		
		current_settings = apply_settings(current_settings, desired_settings)	#Apply new settings to A/C and put new A/C settings into variable
	
	
		#Wait for 1 minute while checking for flag to stop climate controlling
		for i in xrange(1, 60):
			sleep(1)
			
			#Kill flag from server
			if e.isSet():
				log_event("Temp control thread has been stopped")
				exit()
			
			#Break out of For loop after 1 minute
			tc = datetime.datetime.now() - startTime
			tc = tc.total_seconds()
			
			if tc > 61:
				break
		
		
		#Decrement current settings TTL
		current_settings.TTL -= 1

		#Get current settings from A/C
		if current_settings.TTL <= 0:
			current_settings = get_ac_settings(current_settings)
			
		
		log_event("Change in room temp is " + str(get_temp.get_room_temp() - room_temp) + " degrees")

		#Logging
		timeChange = datetime.datetime.now() - startTime
		timeChange = timeChange.total_seconds()
		log_event("Number of seconds to complete this cycle: " + str(timeChange))
		log_event("Current settings TTL: " + str(current_settings.TTL))
		
		log_event('')
		
		desired_settings = None
		
		

if __name__ == "__main__":

	thermostat(27)
