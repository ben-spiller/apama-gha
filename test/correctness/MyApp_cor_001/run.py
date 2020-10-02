# Sample PySys testcase
# Copyright (c) 2015-2016, 2018-2020 Software AG, Darmstadt, Germany and/or Software AG USA Inc., Reston, VA, USA, and/or its subsidiaries and/or its affiliates and/or their licensors. 
# Use, reproduction, transfer, publication or disclosure is prohibited except as specifically provided for in your License Agreement with Software AG 

import pysys
from pysys.constants import *
import apama.correlator

class PySysTest(pysys.basetest.BaseTest):

	def execute(self):
		# Start an instance of the correlator (on an automatically generated free port) 
		correlator = apama.correlator.CorrelatorHelper(self, name='testCorrelator')
		correlator.start(logfile='testCorrelator.log')
		
		# Inject the application EPL and any test monitors
		correlator.injectEPL([self.project.appHome+'/monitors/SensorMonitorApp.mon'])
		
		# This is how to wait for a log message, with automatic aborting if an error occurs while waiting
		# (though not strictly necessary in this testcase)
		self.waitForGrep('testCorrelator.log', expr="Loaded SensorMonitor", process=correlator.process, errorExpr=[' (ERROR|FATAL) .*'])
		
		# We can send in events to configure our sensors as we need them for the test
		correlator.sendEventStrings(
			'apamax.myapp.AddSensor("TempSensor001",100)',
			'apamax.myapp.AddSensor("TempSensor002",800)',
		)

		# Send in some representative sample data from .evt file in the Input/ directory, to exercise our application
		correlator.send([self.project.appHome+'/events/TemperatureEvents.evt'])
			
		# Wait for all events to be processed (the flush() approach works well for simple cases, but if you need to 
		# wait for any external events or time listeners then you'll need waitForGrep instead). 
		correlator.flush()
	
	def validate(self):
		# Best practice is to always check for errors in the the correlator log file (you can add ignores for any 
		# that you are expecting)
		self.assertGrep('testCorrelator.log', expr=' (ERROR|FATAL|Failed to parse) .*', contains=False, ignores=[])

