import serial
#import MySQLdb
import time
import re
import datetime
import logging
import socket
import multiprocessing
import os
import sys
import json
import httplib
import urllib2
import json
import serial.tools.list_ports
import sys, traceback
from subprocess import Popen, PIPE
import fcntl

import BlynkLib

USBDEVFS_RESET= 21780

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class APServer(object):
# id nodo
#	10: ARDUINO_EMONTX
	nodeids = {
		"0":{"GET_CMD":"GET_CMD"},
		"10":{"POWER_SOLAR":"W", "CURRENT_SOLAR":"A", "VOLTAGE":"V", "TEMP_TERRAZZO":"&deg;"},
		"30":{"CURRENT_CASA":"A", "TEMP_DISIMPEGNO":"&deg;", "TEMP_SALOTTO":"&deg;", "TEMP_SOTTOTETTO":"&deg;"},
		"40":{"CURRENT_TERMO":"A", "LIGHT_TERRAZZO":"&perc;"}
	}
	domain = "192.168.1.9"
	emoncmspath = "emoncms"
	apikey = "2a4e7605bb826a82ef3a54f4ff0267ed"
	urlJobs = "http://192.168.1.9/temp/jobs.php"
	jobsUsr = "anto"
	jobsPwd = "resistore"

	sendingCmd = False

	lastUSBreading = 0

	def srvinit(self):
		#self.dbconn = MySQLdb.connect('192.168.1.12', 'apdb', 'pwd4apdb', 'apdb')
		#self.dbconn.autocommit(True)
		#self.dbconn.ping(True)
		#print self.dbconn
		key="START"
		self.srvaddress = socket.gethostbyname(socket.gethostname())
		self.srvpid = os.getpid()
		params = {}
		value = params["pid"] = str(self.srvpid)
		#self.log_event("SRV", key, value, self.srvaddress, json.dumps(params))

	def __init__(self):
			self.srvinit()

	def log(self, nodeid, key, value) :
		ts = time.time()
		timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
		print bcolors.BOLD+timestamp+bcolors.ENDC+": "+nodeid+" "+key+" "+bcolors.OKBLUE+value+bcolors.ENDC

	def log_emoncms(self, nodeid, key, value):
		conn = httplib.HTTPConnection(self.domain)
		url = "/"+self.emoncmspath+"/input/post.json?apikey="+self.apikey+"&node="+nodeid+"&json={"+key+":"+value+"}"
		try:
			conn.request("GET", url)
		except Exception as e:
			print "HTTP error: %s" % str(e)



	def parsecmd(self, cmd, logger):
		sendingCmd = True
		if (cmd == 'GET_CMD') :
			#print("Requesting command...")
			url = self.urlJobs+'?req_cmd=HEATERS'
			password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
			password_mgr.add_password(None, url, self.jobsUsr, self.jobsPwd)
			handler = urllib2.HTTPBasicAuthHandler(password_mgr)
			opener = urllib2.build_opener(handler)
			urllib2.install_opener(opener)
			response = urllib2.urlopen(url)
			jsonData = json.loads(response.read())
			serverCmd = "0 NOOP:NOOP"
			id = "-1"
			if len(jsonData['data']) > 0 :
				id = str(jsonData['data'][0]["id"])
				serverCmd = id+" "+str(jsonData['data'][0]["cmd"])
				#print("Sending: "+serverCmd)
				self.log("", "", "-> "+serverCmd)
			if (serverCmd != "") :
				self.serialwriteACM(serverCmd, logger)
				time.sleep(0.5)
				#print "Waiting response..."
				myline = self.serialreadACM(logger)
				#print "...done"

				if (serverCmd != '0 NOOP:NOOP' and myline != '') :
					#print('Result: '+myline)
					self.log("", "", "<- "+myline.strip())
					tokens = myline.split(":")
					if (len(tokens) > 1 and tokens[0] == id) :
						url = self.urlJobs+'?job_id='+tokens[0]
						#print url
						password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
						password_mgr.add_password(None, url, self.jobsUsr, self.jobsPwd)
						handler = urllib2.HTTPBasicAuthHandler(password_mgr)
						opener = urllib2.build_opener(handler)
						urllib2.install_opener(opener)
						response = urllib2.urlopen(url)

		sendingCmd = False


	def parsereading(self, myline, logger):
		#Some data was received
		p = re.compile('[^:\s]+:[^:\s]+:[\d|\.|-]+:[^\s]+')
		vals = p.findall(myline)
		if (len(vals) > 0):
			for val in vals:
				info = val.split(':')
				if (len(info) == 4 and info[0] != 'MILLIS'):
					#logger.debug('nodeId: '+info[0])
					if (info[0] == "0" and info[1] in self.nodeids[info[0]]) :
						#logger.debug(timestamp+" "+info[1])
						self.parsecmd(info[1], logger)
					else :
						if (info[0] in self.nodeids) :
							if (info[1] in self.nodeids[info[0]]) :
								self.log_emoncms(info[0], info[1], info[2])
								self.log(info[0], info[1], info[2])
						else :
							print timestamp+" "+str(val)+" not ok !"	

	def serialwriteACM(self, cmd, logger):
		myline = ""
		try:
			if(self.serACM.isOpen() == False):
				self.serACM.open()
			cmdToSend = cmd+'\r'
			self.serACM.write(cmdToSend.encode())
			self.serACM.flushOutput()
		except IOError as e:
			self.initserialACM(logger)
		except TypeError as e:
			logger.debug(e)
			exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			self.serACM.flushInput()
			self.serACM.close()
			time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(2)
			self.initserialACM(logger)
			#time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(5)
		except serial.SerialException as e:
			logger.debug(e)
			print "Error on line "+format(sys.exc_info()[-1].tb_lineno)()
			self.serACM.flushInput()
			self.serACM.close()
			time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(2)
			self.initserialACM(logger)

	def serialreadACM(self, logger):
		myline = ""
		try:
			if(self.serACM.isOpen() == False):
				self.serACM.open()
			start = time.time()
			msg = ""
			while (self.serACM.inWaiting() == 0):
				now = time.time()
				diff = 1000 * (now - start)
				tokens = str(diff).split(".")
				intdiff = int(tokens[0])
				if (intdiff % 1000 == 0 and intdiff > 0) :
					msg += tokens[0]+'...'
			if (self.serACM.inWaiting() > 0):
				myline = self.serACM.readline()
				if (myline != "" and myline != "\r" and myline != "\n" and len(msg) > 1) :
					print bcolors.WARNING+msg+bcolors.ENDC
					self.serACM.flushInput()
		except IOError as e:
			self.initserialACM(logger)
		except TypeError as e:
			logger.debug(e)
			exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			self.serACM.flushInput()
			self.serACM.close()
			time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(2)
			self.initserialACM(logger)
			#time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(5)
		except serial.SerialException as e:
			logger.debug(e)
			print "Error on line "+format(sys.exc_info()[-1].tb_lineno)()
			self.serACM.flushInput()
			self.serACM.close()
			time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(2)
			self.initserialACM(logger)
		return myline

	def initserialACM(self, logger):
		#print "Resetting ttyACM..."
		path = ""
		for port_no, description, address in serial.tools.list_ports.comports() :
			if 'ACM' in description:
				#print(address)
				path = port_no
				break
		if path != "" :
			print "Using "+path
			try:
				self.serACM = serial.Serial(path,
					baudrate=9600,
					bytesize=serial.EIGHTBITS,
					parity=serial.PARITY_NONE,
					stopbits=serial.STOPBITS_ONE,
					timeout=1,
					xonxoff=0,
					rtscts=0
				)

				if(self.serACM.isOpen() == False):
					self.serACM.open() 
				self.serACM.setDTR(False)
				self.serACM.flushInput()
				time.sleep(1)
				self.serACM.setDTR(True)
			except IOError as e:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				print "*** print_tb:"
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				self.resetserial("Arduino")
				self.initserialACM(logger)
		else:
			print("Serial not found !")
			time.sleep(2)
			self.initserialACM(logger)
		return path

	def serialreadUSB(self, logger):
		print("serialreadUSB")
		myline = ""
		try:
			while(self.serUSB.isOpen() == False):
				self.serUSB.open()
			currenttime = time.time()
			timediff = currenttime - self.lastUSBreading
			if (self.serUSB.inWaiting() > 0):
				self.lastUSBreading = time.time()
				print (str(self.serUSB.inWaiting())+" chars waiting")
				myline = self.serUSB.readline()
				self.serUSB.flushInput()
			elif timediff > 60:
				print "No new readings from more than "+str(timediff)+" secs"
				print str(currenttime)+" "+str(self.lastUSBreading)
				self.resetserial("FT232")
				time.sleep(5)
				self.initserialUSB(logger)
		except IOError as e:
			self.initserialUSB(logger)
		except TypeError as e:
			logger.debug(e)
			exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			self.serUSB.flushInput()
			self.serUSB.close()
			time.sleep(2)
			self.initserialUSB(logger)
			#time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(5)
		except serial.SerialException as e:
			logger.debug(e)
			exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			self.serUSB.flushInput()
			self.serUSB.close()
			time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(2)
			self.initserialUSB(logger)
			#time.sleep(5)
		else:
			if (len(myline) > 0) :
				logger.debug(myline);
				self.parsereading(myline, logger)
		#return path

	def initserialUSB(self, logger):
		print "Resetting ttyUSB..."
		path = ""
		for port_no, description, address in serial.tools.list_ports.comports() :
			if 'USB' in description:
				print(address)
				path = port_no
				break

		if path != "" :
			print "Opening serial on "+path+"..."
			try:
				self.serUSB = serial.Serial(path,
					baudrate=9600,
					bytesize=serial.EIGHTBITS,
					parity=serial.PARITY_NONE,
					stopbits=serial.STOPBITS_ONE,
					timeout=1,
					xonxoff=0,
					rtscts=True,
					dsrdtr=True
					#rtscts=0
				)
				while(self.serUSB.isOpen() == False):
					self.serUSB.open()
				self.serUSB.setDTR(False)
				self.serUSB.flushInput()
				time.sleep(5)
				self.serUSB.setDTR(True)
				print path+" ready !"
			except IOError as e:
				print "IOError after opening USB..."
				exc_type, exc_value, exc_traceback = sys.exc_info()
				print "*** print_tb:"
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				while (self.serUSB.isOpen() == True):
					self.serUSB.flushInput()
					self.serUSB.close()
				time.exc_type, exc_value, exc_traceback = sys.exc_info()
				print "*** print_tb:"
				time.sleep(5)
				self.resetserial("FT232")
				self.initserialUSB(logger)
		else:
			print("Serial not found waiting 10 secs...!")
			time.sleep(10)
			self.initserialUSB(logger)
		return path				

	def resetserial(self, driver):
		try:
			lsusb_out = Popen("lsusb | grep -i %s"%driver, shell=True, bufsize=64, stdin=PIPE, stdout=PIPE, close_fds=True).stdout.read().strip().split()
			bus = lsusb_out[1]
			device = lsusb_out[3][:-1]
			f = open("/dev/bus/usb/%s/%s"%(bus, device), 'w', os.O_WRONLY)
			fcntl.ioctl(f, USBDEVFS_RESET, 0)
		except Exception, msg:
			print "failed to reset device:", msg
		

	def serialsrv(self):
		logging.basicConfig(level=logging.DEBUG)
		logger = logging.getLogger("process-serial")
		logger.debug("Starting serial process")
		self.resetserial("FT232")
		pathACM = self.initserialACM(logger)
		#pathUSB = self.initserialUSB(logger)
		try:
			while True:
				while self.sendingCmd:
					print "."
				myline = self.serialreadACM(logger)
				if (myline != '') :
					#print('Got: '+myline)
					self.parsereading(myline,logger)
				sys.stdout.flush()
		except:
			logger.exception("Problem handling request")
		finally:
			logger.debug("Closing serial process")

	def start(self):
		self.serialsrv()


class APServerBlynk(object):
# id nodo
#	10: ARDUINO_EMONTX
	nodeids = {
		"10":{"POWER_SOLAR":30, "CURRENT_SOLAR":31, "VOLTAGE":0, "TEMP_TERRAZZO":6},
	}

	authToken = "736662121c984b3da398b973b54a3bd3"
	port = 8080

	domain = "192.168.1.9"
	emoncmspath = "emoncms"
	apikey = "2a4e7605bb826a82ef3a54f4ff0267ed"
	urlJobs = "http://192.168.1.9/temp/jobs.php"
	jobsUsr = "anto"
	jobsPwd = "resistore"

	sendingCmd = False

	lastUSBreading = 0

	@blynk.ON("connected")
	def blynk_connected(self, ping):
		print('Blynk ready. Ping:', ping, 'ms')

	@blynk.ON("disconnected")
	def blynk_disconnected(self):
		print('Blynk disconnected')

	@blynk.ON("V*")
	def blynk_handle_vpins(self, pin, value):
		print("V{} value: {}".format(pin, value))

	@blynk.ON("readV*")
	def blynk_handle_vpins_read(self, pin):
		print("Server asks a value for V{}".format(pin))
		blynk.virtual_write(pin, 0)

	def srvinit(self):
		key="START"
		self.srvaddress = socket.gethostbyname(socket.gethostname())
		self.srvpid = os.getpid()
		#params = {}, True, False
		#value = params["pid"] = str(self.srvpid)
		# Initialize Blynk

		self.blynk = BlynkLib.Blynk(self.authToken, server=self.domain, port=self.port)

	def __init__(self):
			self.srvinit()

	def log(self, nodeid, key, value) :
		ts = time.time()
		timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
		print bcolors.BOLD+timestamp+bcolors.ENDC+": "+nodeid+" "+key+" "+bcolors.OKBLUE+value+bcolors.ENDC

	def log_blynk(self, nodeid, key, value):
		try:
			print str(key)+" "+str(value)
			self.blynk.virtual_write(key, abs(float(value)))
		except Exception as e:
			print "Blynk error: %s" % str(e)

	def log_emoncms(self, nodeid, key, value):
		conn = httplib.HTTPConnection(self.domain)
		url = "/"+self.emoncmspath+"/input/post.json?apikey="+self.apikey+"&node="+nodeid+"&json={"+key+":"+value+"}"
		try:
			conn.request("GET", url)
		except Exception as e:
			print "HTTP error: %s" % str(e)

	def parsereading(self, myline, logger):
		#Some data was received
		p = re.compile('[^:\s]+:[^:\s]+:[\d|\.|-]+:[^\s]+')
		vals = p.findall(myline)
		if (len(vals) > 0):
			for val in vals:
				info = val.split(':')
				if (len(info) == 4 and info[0] != 'MILLIS'):
					#logger.debug('nodeId: '+info[0])	
					if (info[0] in self.nodeids) :
						if (info[1] in self.nodeids[info[0]]) :
							self.log_blynk(info[0], self.nodeids[info[0]][info[1]], info[2])
							self.log_emoncms(info[0], info[1], info[2])
							self.log(info[0], info[1], info[2])
					else :
						ts = time.time()
						timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
						print timestamp+" "+str(val)+" not ok !"	

	def serialreadACM(self, logger):
		myline = ""
		try:
			if(self.serACM.isOpen() == False):
				self.serACM.open()
			start = time.time()
			msg = ""
			while (self.serACM.inWaiting() == 0):
				now = time.time()
				diff = 1000 * (now - start)
				tokens = str(diff).split(".")
				intdiff = int(tokens[0])
				if (intdiff % 1000 == 0 and intdiff > 0) :
					msg += tokens[0]+'...'
			if (self.serACM.inWaiting() > 0):
				myline = self.serACM.readline()
				if (myline != "" and myline != "\r" and myline != "\n" and len(msg) > 1) :
					print bcolors.WARNING+msg+bcolors.ENDC
					self.serACM.flushInput()
		except IOError as e:
			self.initserialACM(logger)
		except TypeError as e:
			logger.debug(e)
			exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
			self.serACM.flushInput()
			self.serACM.close()
			time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(2)
			self.initserialACM(logger)
			#time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(5)
		except serial.SerialException as e:
			logger.debug(e)
			print "Error on line "+format(sys.exc_info()[-1].tb_lineno)()
			self.serACM.flushInput()
			self.serACM.close()
			time.exc_type, exc_value, exc_traceback = sys.exc_info()
			print "*** print_tb:"
			time.sleep(2)
			self.initserialACM(logger)
		return myline

	def initserialACM(self, logger):
		#print "Resetting ttyACM..."
		path = ""
		for port_no, description, address in serial.tools.list_ports.comports() :
			if 'ACM' in description:
				#print(address)
				path = port_no
				break
		if path != "" :
			print "Using "+path
			try:
				self.serACM = serial.Serial(path,
					baudrate=9600,
					bytesize=serial.EIGHTBITS,
					parity=serial.PARITY_NONE,
					stopbits=serial.STOPBITS_ONE,
					timeout=1,
					xonxoff=0,
					rtscts=0
				)

				if(self.serACM.isOpen() == False):
					self.serACM.open() 
				self.serACM.setDTR(False)
				self.serACM.flushInput()
				time.sleep(1)
				self.serACM.setDTR(True)
			except IOError as e:
				exc_type, exc_value, exc_traceback = sys.exc_info()
				print "*** print_tb:"
				traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
				self.resetserial("Arduino")
				self.initserialACM(logger)
		else:
			print("Serial not found !")
			time.sleep(2)
			self.initserialACM(logger)
		return path		

	def resetserial(self, driver):
		try:
			lsusb_out = Popen("lsusb | grep -i %s"%driver, shell=True, bufsize=64, stdin=PIPE, stdout=PIPE, close_fds=True).stdout.read().strip().split()
			bus = lsusb_out[1]
			device = lsusb_out[3][:-1]
			f = open("/dev/bus/usb/%s/%s"%(bus, device), 'w', os.O_WRONLY)
			fcntl.ioctl(f, USBDEVFS_RESET, 0)
		except Exception, msg:
			print "failed to reset device:", msg

	def serialread(self):
		try:
			myline = self.serialreadACM(logger)
			if (myline != '') :
				#print('Got: '+myline)
				self.parsereading(myline,logger)
				time.sleep(5)
			sys.stdout.flush()
		except:
			logger.exception("Problem handling request")
		finally:
			logger.debug("Closing serial process")

	def serialsrv(self):
		logging.basicConfig(level=logging.DEBUG)
		logger = logging.getLogger("process-serial")
		logger.debug("Starting serial process")
		self.resetserial("FT232")
		pathACM = self.initserialACM(logger)
		#pathUSB = self.initserialUSB(logger)
		try:
			while True:
				try: 
					self.blynk.run()
					self.serialread()

				#except BrokenPipeError as e:
				#	print('Socket error {}'.format(e))
				#	blynk.on_connect(self.blynkconnected)
				#except IOError as e:
				except:
					#if e.Errno == Errno.EPIPE:
						#print('EPIPE error {}'.format(e))
					self.blynk.on_connect(self.blynkconnected)
					#else:
						#print("Unexpected error:", sys.exc_info()[0])
						#raise
				
				
				#myline = self.serialreadACM(logger)
				#if (myline != '') :
					#print('Got: '+myline)
					#self.parsereading(myline,logger)
					#time.sleep(5)
				#sys.stdout.flush()
		except:
			logger.exception("Problem handling request")
		finally:
			logger.debug("Closing serial process")

	def start(self):
		self.serialsrv()


def main ():
	sys.stdout = open("/var/log/domotic.log", "w")
	server = APServerBlynk()
	server.start()

if __name__ == "__main__":
		main()
