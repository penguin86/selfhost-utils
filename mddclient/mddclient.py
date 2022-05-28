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


NAME = 'mddclient'
VERSION = '0.1'
DESCRIPTION = 'A DynamicDns client like ddclient, but supporting multiple (sub)domains'

class Main:

	def __init__(self, configPath):
		''' Reads the config '''
		self._log = logging.getLogger('main')

		if not os.path.exists(configPath) or not os.path.isfile(configPath):
			raise ValueError('configPath must be a file')

		self.config = configparser.ConfigParser()
		self.config.read(configPath)

	def run(self):
		''' Makes the update requests '''

		for section in self.config:
			if section == 'DEFAULT':
				# Main domain
				# TODO
				continue

			s = Settings(section, self.config)
			if s.disabled:
				self._log.info('Ignoring disabled domain "{}"'.format(section))
				continue

			self._log.info('Updating "{}"'.format(section))

			# TODO: subdomain update request


class Settings:
	''' Represents settings for a check '''

	EMAIL_LIST_SEP = ','

	def __init__(self, name, config):
		self.config = config

		## Section name
		self.name = name
		
		## Settings
		self.disabled = self.getBoolean(name, 'DISABLED', False)
		self.optimize = self.getBoolean(name, 'OPTIMIZE_API_CALLS', True)

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
	args = parser.parse_args()

	if args.quiet:
		level = logging.WARNING
	else:
		level = logging.INFO
	logging.basicConfig(level=level)

	try:
		main = Main(args.configFile)
		main.run()
	except Exception as e:
		logging.critical(traceback.format_exc())
		print('ERROR: {}'.format(e))
		sys.exit(1)

	sys.exit(0)
