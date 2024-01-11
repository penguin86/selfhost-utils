#!/usr/bin/env python3

""" @package docstring
Mddclient

A DynamicDns client like ddclient, but supporting multiple (sub)domains,
every one in its autonomous request.

Installation:
- Copy mddclient.cfg in /usr/local/etc/mddclient.cfg and customize it
- Copy mddclient.py in /usr/local/bin/mddclient.py

Usage:
Place a cron entry like this one:

* * * * *     root    python3 /usr/local/bin/mddclient.py /usr/local/etc/mddclient.cfg

Exit codes:
0: success
1: unmanaged error (crash)
2: managed error (could not update due to bad config/server error)

For more informations on dyndns2 protocol: https://help.dyn.com/remote-access-api/

@author Daniele Verducci <daniele.verducci@ichibi.eu>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
import sys
import logging
import configparser
import traceback
import requests
import re
import datetime
import json


NAME = 'mddclient'
VERSION = '0.2'
DESCRIPTION = 'A DynamicDns client like ddclient, but supporting multiple (sub)domains'
STATUS_FILE = '/tmp/mddclient.tmp'
CHECKIP_REQUEST_ADDR = 'http://checkip.dyndns.org'
CHECKIP_RESPONSE_PARSER = '<body>Current IP Address: (\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})</body>'
DDCLIENT2_REQUEST_ADDR = "https://{}/nic/update?system=dyndns&hostname={}&myip={}"
DDCLIENT2_RESPONSE_PARSER = '^(nochg|no_change|good) (\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})$'
USER_AGENT = 'Selfhost Utils Mddclient ' + VERSION

class Main:

	def __init__(self, configPath):
		''' Reads the config '''
		self._log = logging.getLogger('main')

		if not os.path.exists(configPath) or not os.path.isfile(configPath):
			raise ValueError('configPath must be a file')

		self.config = configparser.ConfigParser()
		self.config.read(configPath)

	def run(self, force, printStatusAndExit):
		''' Makes the update requests '''

		# Load status
		status = Status()

		if printStatusAndExit:
			status.print()
			return True

		# Check current ip
		currentIp = self.getCurrentIp()
		if (currentIp == None):
			return False

		self._log.info('Current ip is {}'.format(currentIp))

		if currentIp == status.getIp():
			self._log.info('Ip is up-to-date.')
			if force:
				self._log.info('User requested forced refresh.')
			else:
				self._log.info('Nothing to do.')
				status.save(True, False)
				return

		success = True
		updated = False
		for section in self.config:
			s = Settings(section, self.config)
			if s.name == 'DEFAULT':
				continue

			self._log.info('Updating "{}"'.format(section))
			try:
				newIpAddr = self.update(s.ddserver, s.dduser, s.ddpass, s.domain, currentIp)
				self._log.info('Success update {} to addr {}'.format(s.domain, newIpAddr))
				updated = True
			except Exception as e:
				self._log.error('Error while updating {}: {}'.format(s.domain, e))
				success = False

		# Save current ip
		if success:
			status.setIp(currentIp)

		status.save(success, updated)

		return success

	def getCurrentIp(self):
		'''Obtains current IP from checkip.dyndns.org'''
		response = requests.get(CHECKIP_REQUEST_ADDR)

		match = re.search(CHECKIP_RESPONSE_PARSER, response.text, re.MULTILINE)
		if not match:
			self._log.error('Unable to obtain new IP addr: Response format not valid: {}'.format(response.text))
			return
		groups = match.groups()
		if len(groups) != 1:
			self._log.error('Unable to obtain new IP addr: Unable to parse response: {}'.format(response.text))
			return

		return groups[0]

	def update(self, server, user, password, domain, ip):
		apiUrl = DDCLIENT2_REQUEST_ADDR.format(server, domain, ip)
		try:
			response = requests.get(apiUrl, auth=(user, password), headers={"User-Agent": USER_AGENT})
		except requests.ConnectionError:
			raise Exception('Server {} is unreachable'.format(server))

		match = re.search(DDCLIENT2_RESPONSE_PARSER, response.text)
		if not match:
			raise Exception('Response format not valid: {}'.format(response.text))
		groups = match.groups()
		if len(groups) != 2:
			raise Exception('Unable to parse response: {}'.format(response.text))

		operationResult = groups[0]
		ipAddr = groups[1]

		# Check operation result and return appropriate errors
		if operationResult == 'good':
			# Success!
			return ipAddr
		elif operationResult == 'nochg' or operationResult == 'no_change':
			# Should not happen: IP didn't need update
			self._log.warning('Ip addres didn\'t need update: this should happen only at first run')
			return ipAddr
		elif operationResult == 'badauth':
			raise Exception('The username and password pair do not match a real user')
		elif operationResult == '!donator':
			raise Exception('Option available only to credited users, but the user is not a credited user')
		elif operationResult == 'notfqdn':
			raise Exception('The hostname specified is not a fully-qualified domain name (not in the form hostname.dyndns.org or domain.com).')
		elif operationResult == 'nohost':
			raise Exception('The hostname specified does not exist in this user account')
		elif operationResult == 'numhost':
			raise Exception('Too many hosts specified in an update')
		elif operationResult == 'abuse':
			raise Exception('The hostname specified is blocked for update abuse')
		elif operationResult == 'badagent':
			raise Exception('The user agent was not sent or HTTP method is not permitted')
		elif operationResult == 'dnserr':
			raise Exception('DNS error encountered')
		elif operationResult == '911':
			raise Exception('There is a problem or scheduled maintenance on server side')
		else:
			raise Exception('Server returned an unknown result code: {}'.format(operationResult))


class Status:
	''' Represents the current status '''

	def __init__(self):
		try:
			with open(STATUS_FILE, 'r') as openfile:
				self.status = json.load(openfile)
		except FileNotFoundError:
			self.status =  {
				'lastRun': None,
				'lastRunSuccess': None,
				'lastUpdate': None,
				'lastIpAddr': None,
			}

	def save(self, success, updated):
		self.status['lastRun'] = str(datetime.datetime.now())
		self.status['lastRunSuccess'] = success
		if updated:
			self.status['lastUpdate'] = str(datetime.datetime.now())
		jo = json.dumps(self.status)
		with open(STATUS_FILE, "w") as outfile:
			outfile.write(jo)

	def setIp(self, ip):
		self.status['lastIpAddr'] = ip

	def getIp(self):
		return self.status['lastIpAddr']

	def print(self):
		for k in self.status:
			print('{}: {}'.format(k, self.status[k]))


class Settings:
	''' Represents settings for a domain '''

	def __init__(self, name, config):
		self.config = config

		## Section name
		self.name = name

		## DynDNS server data
		self.ddserver = self.getStr(name, 'SERVER', None)
		self.dduser = self.getStr(name, 'LOGIN', None)
		self.ddpass = self.getStr(name, 'PASSWORD', None)

		## Domain to update
		self.domain = self.getStr(name, 'DOMAIN', False)

	def getStr(self, name, key, defaultValue):
		try:
			return self.config.get(name, key)
		except configparser.NoOptionError:
			return defaultValue

	def getBoolean(self, name, key, defaultValue):
		try:
			return self.config.getboolean(name, key)
		except configparser.NoOptionError:
			return defaultValue


if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser(
		prog = NAME + '.py',
		description = NAME + ' ' + VERSION + '\n' + DESCRIPTION,
		formatter_class = argparse.RawTextHelpFormatter
	)
	parser.add_argument('configFile', help="configuration file path")
	parser.add_argument('-q', '--quiet', action='store_true', help="suppress non-essential output")
	parser.add_argument('-f', '--force', action='store_true', help="force update")
	parser.add_argument('-s', '--status', action='store_true', help="print current status and exit doing nothing")
	args = parser.parse_args()

	if args.quiet:
		level = logging.WARNING
	else:
		level = logging.INFO
	logging.basicConfig(
		format='%(asctime)s %(levelname)-8s %(message)s',
		level=level,
		datefmt='%Y-%m-%d %H:%M:%S'
	)

	try:
		main = Main(args.configFile)
		if not main.run(args.force, args.status):
			sys.exit(2)
	except Exception as e:
		logging.critical(traceback.format_exc())
		print('FATAL ERROR: {}'.format(e))
		sys.exit(1)

	sys.exit(0)
