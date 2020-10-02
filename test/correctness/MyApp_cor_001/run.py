# Sample PySys testcase
# Copyright (c) 2015-2016, 2018-2020 Software AG, Darmstadt, Germany and/or Software AG USA Inc., Reston, VA, USA, and/or its subsidiaries and/or its affiliates and/or their licensors. 
# Use, reproduction, transfer, publication or disclosure is prohibited except as specifically provided for in your License Agreement with Software AG 

import pysys
from pysys.constants import *

class PySysTest(pysys.basetest.BaseTest):

	def execute(self):
		# Start an instance of the correlator (on an automatically generated free port) 
		correlator = self.apama.startCorrelator('testCorrelator')
		
		# This test monitor produces a line in the correlator log with a JSON representation of each event sent to the 
		# specified channel(s), which provides a very convenient way to check the results
		# In some tests it's helpful to include the channel containing the inputs (e.g. Factory1 in this case) as well 
		# as the outputs so you can see the ordering relationship between input and output clearly
		correlator.injectTestEventLogger(channels=['Alerts', 'Factory1'])

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
		
		# Wait for the expected number of events to appear in the log file, aborting if there's an error or event 
		# parsing failure (NB: don't try to use regular expressions to parse the actual contents of your events) 
		self.waitForGrep('testCorrelator.log', expr='-- Got test event: .*apamax.myapp.Alert', condition=">=3+2", 
			errorExpr=[' (ERROR|FATAL|Failed to parse) .*'])
	
	
	def validate(self):
		# Best practice is to always check for errors in the the correlator log file (you can add ignores for any 
		# that you are expecting)
		self.assertGrep('testCorrelator.log', expr=' (ERROR|FATAL|Failed to parse) .*', contains=False, ignores=[])

		# The easiest way to validate the output events is usually to use extractEventLoggerOutput() to get events 
		# written by injectEventLogger() into a Python dictionary. The fields and events of interest can be easily 
		# extracted using the power of Python [...] list comprehensions
		sensor1_temps = [ 
			# Extract only the field value(s) we care about (allows us to ignore unimportant information, timestamps, etc):
			(evt['temperature']) for evt in self.apama.extractEventLoggerOutput('testCorrelator.log')
			
			# Filter to include the desired subset of events:
			if evt['.eventType']=='apamax.myapp.Alert' and evt['sensorId']=='TempSensor001'
			]
		self.assertThat('sensor1_temps == expected', sensor1_temps=sensor1_temps, expected=[
				111.0,
				120,
				145.2,
			])

		# It's easy to write sophisticated verification conditions using the values extracted from the events
		self.assertThat('min(sensor1_temps) >= expected', sensor1_temps=sensor1_temps, expected=100*1.02)
		self.assertThat('50 <= sensor1_temps[0] <= 200', sensor1_temps=sensor1_temps)

		# For cases where you have many events, or want to use most of the event fields not just one or two, 
		# it may be easier to generate a file containing the fields and events of interest and then diff them
		self.write_text('sensor2_output.txt', '\n'.join(
			str( {field:val for (field,val) in evt.items() if field not in ['time', 'requestId'] })
				for evt in self.apama.extractEventLoggerOutput('testCorrelator.log')
				if evt['.eventType']=='apamax.myapp.Alert' and evt['sensorId']=='TempSensor002'), 
			encoding='utf-8')
		self.assertDiff('sensor2_output.txt', encoding='utf-8')
