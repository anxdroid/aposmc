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

authToken = "1f265075b96e449d8efd602338442b22"
port = 8080
ip = "192.168.1.9"
blynk = BlynkLib.Blynk(authToken, server=ip, port=port)
timer = BlynkTimer()

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

def main():
	while True:
		blynk.run()
		timer.run()

if __name__ == "__main__":
		main()