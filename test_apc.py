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
import sys, traceback
from subprocess import Popen, PIPE
import fcntl

import BlynkLib
from BlynkTimer import BlynkTimer

#from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

authToken = "1f265075b96e449d8efd602338442b22"
port = 8080
ip = "192.168.1.9"
blynk = BlynkLib.Blynk(authToken, server=ip, port=port)
timer = BlynkTimer()
lastStatus = ""
lastPerc = 0
currStatus = ""
currPerc = 0

vpins = {
        "STATUS" : 0,
        "BCHARGE" : 1,
        "TIMELEFT" : 2
        }

@blynk.ON("connected")
def blynk_connected(ping):
	print('Blynk ready. Ping:', ping, 'ms')

@blynk.ON("disconnected")
def blynk_disconnected():
	print('Blynk disconnected')
	blynk = BlynkLib.Blynk(authToken, server=ip, port=port)

@blynk.ON("V*")
def blynk_handle_vpins(pin, value):
	print("V{} value: {}".format(pin, value))

@blynk.ON("readV*")
def blynk_handle_vpins_read(pin):
	print("Server asks a value for V{}".format(pin))
	blynk.virtual_write(pin, 0)

def readVal():
    global currStatus
    global currPerc
    global lastStatus
    global lastPerc
    #print("Reading value...")
    cmd = 'apcaccess status'
    myCmd = os.popen(cmd).read()
    #print(myCmd)
    # NOMINV   : 230 Volts
    p = re.compile('[\r\n]*([^:]+):([^\n\r]+)')
    groups = p.findall(myCmd)
    if (len(groups) > 0):
        for g in groups:
            k = g[0].strip()
            v = g[1].strip().replace(" Percent", "").replace(" Minutes", "")
            if (k == 'BCHARGE' or k == 'TIMELEFT') :
                v = float(v)
            if (k == "BCHARGE") :
                currPerc = v
            if (k == "STATUS") :
                currStatus = v
            if (k in vpins) :
                #if (currPerc != 0) :
                #    print currStatus+" - "+str(currPerc)
                print k+" => V"+str(vpins[k])+' : '+str(v)
                sys.stdout.flush()
                blynk.virtual_write(vpins[k], v)
                if (currPerc != lastPerc) :
                    print currStatus+" - "+str(currPerc)
                    contents = urllib2.urlopen("https://api.telegram.org/bot738992030:AAHcuMiGmx8stdyy6bVkKWCIB5-JHjdgd9M/sendMessage?chat_id=-205991625&text="+currStatus+" "+str(currPerc)+"%").read()
                    lastStatus = currStatus
                    lastPerc = currPerc

def main():
        sys.stdout = open("/var/log/domotic.log", "w")
        timer.set_interval(1, readVal)
	while True:
		blynk.run()
		timer.run()

if __name__ == "__main__":
		main()
