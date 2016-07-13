#!/usr/bin/python

import random
import datetime 
from time import sleep


class PID_Controller(object):

	def Compute(self):
	
		error = 0
		dInput = 0 
		
		now = datetime.datetime.now()
		timeChange = now - self.lastTime
		timeChange = timeChange.total_seconds()
		
		#if timeChange >= self.SampleTime:
		
		error = self.Setpoint - self.Input
			
		self.ITerm += self.ki * error
		
		if self.ITerm > self.outMax:
			self.ITerm = self.outMax
		
		elif self.ITerm < self.outMin:
			self.ITerm = self.outMin

		dInput = self.Input - self.lastInput
		
		self.Output = self.kp * error + self.ITerm - self.kd * dInput
		
		print str(self.Output) + ' = ' + str(self.kp) + ' * ' + str(error) + ' + ' + str(self.ITerm) + ' - ' + str(self.kd) + ' * ' + str(dInput)
		
		print "Calculated output: " + str(self.Output)
		
		if self.Output > self.outMax:
			self.Output = self.outMax
		
		elif self.Output < self.outMin:
			self.Output = self.outMin
			
		self.lastInput = self.Input
		self.lastTime = datetime.datetime.now()
			

	def SetTunings(self, KP, KI, KD):
	
		self.kp = KP
		self.ki = KI
		self.kd = KD 
		

	def __init__(self, sp, ct, mintemp, maxtemp):
		
		self.lastTime = datetime.datetime.now()
		
		self.Setpoint = sp
		
		self.Input = ct
		self.Output = ct
		self.ITerm = ct
		self.lastInput = ct
		
		self.kp = 2.1
		self.ki = 0.5
		self.kd = 2
		
		self.SampleTime = 1
		
		self.outMin = mintemp
		self.outMax = maxtemp
				
		
	def update(self, newInput):
	
		print 'Input: ' + str(newInput)
		
		self.Input = newInput
		self.Compute()
		
		print 'Output: ' + str(self.Output)
		
		return float(self.Output)
		



if __name__ == "__main__":

	PID = PID_Controller(25, 25, 20, 34)
		
