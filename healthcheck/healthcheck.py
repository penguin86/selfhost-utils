#!/usr/bin/env python3

""" @package docstring
Self host healthcheck

A simple server monitoring software: ends an email in case of alarm.

Installation:
- Copy healthcheck.cfg in /usr/local/etc/healthcheck.cfg and customize it
- Copy healthcheck.py in /usr/local/bin/healthcheck.py

Usage:
Place a cron entry like this one:

* * * * *     root    python3 /usr/local/bin/healthcheck.py /usr/local/etc/healthcheck.cfg

The script will print current values and issue an alarm sending a mail if any of the values
exceeds the limit configured in healthcheck.cfg

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
import traceback
import subprocess
import configparser
import time
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import smtplib
import socket
import getpass
import re
import locale


NAME = 'healthcheck'
VERSION = '0.1'
DESCRIPTION = 'A simple server monitoring software'
EMAIL_SUBJECT_TPL = 'Host {} failed health check for {}'
EMAIL_MESSAGE_TPL = 'Alarm for sensor {} on host {} on {}: {}'

class Main:

	def __init__(self, configPath):
		''' Sets up locale (needed for parsing numbers) '''
		# Get system locale from $LANG (i.e. "en_GB.UTF-8")
		systemLocale = os.getenv('LANG')
		if not systemLocale:
			raise ValueError('System environment variabile $LANG is not set!')
		
		locale.setlocale(locale.LC_ALL, systemLocale)

		''' Reads the config '''
		self._log = logging.getLogger('main')

		if not os.path.exists(configPath) or not os.path.isfile(configPath):
			raise ValueError('configPath must be a file')

		self.config = configparser.ConfigParser(interpolation=None)	# Disable interpolation because contains regexp
		self.config.read(configPath)
		self.hostname = os.uname()[1]

	def run(self, dryRun):
		''' Runs the health checks '''

		for section in self.config:
			if section == 'DEFAULT':
				continue

			s = Settings(section, self.config)
			if s.disabled:
				self._log.info('Ignoring disabled check "{}"'.format(section))
				continue

			self._log.info('Checking "{}"'.format(section))

			error = self.check(s)
			if error:
				# Alarm!
				logging.warning('Alarm for {}: {}!'.format(section, error))
				if not dryRun:
					if s.mailto:
						self.sendMail(s, error)
					if s.alarmCommand:
						self.executeAlarmCommand(s, error)

	# Calls the provided command, checks the value parsing it with the provided regexp
	# and returns an error string, or null if the value is within its limits
	def check(self, config):
		# Check config
		if not config.command:
			return "bad config: COMMAND is mandatory"
		if not config.regexp:
			return "bad config: REGEXP is mandatory"
		
		# Run command
		stdout = ""
		ret = subprocess.run(config.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		if ret.stderr:
			self._log.info('{} subprocess stderr:\n{}', config.command, ret.stderr.decode())
		if ret.stdout:
			stdout = ret.stdout.decode()
			self._log.debug('{} subprocess stdout:\n{}', config.command, stdout)
		if ret.returncode != 0:
			return 'subprocess {} exited with error code {}'.format(config.command, ret.returncode)
		
		# Parse result with regex
		match = re.search(config.regexp, stdout, re.MULTILINE)
		if not match:
			return 'regexp didn\'t match anything'
		groups = match.groups()
		if len(groups) != 1:
			return 'regexp returns {} groups (expected exactly 1 group)'.format(len(matches))
		detectedValue = groups[0]

		# Compare detected value with equal, not equal, more than and less values
		logging.info('detected {}'.format(detectedValue))
		if config.alarm_string_equal and (detectedValue == config.alarm_string_equal):
			return 'value is "{}"'.format(detectedValue)
		if config.alarm_string_not_equal and (detectedValue != config.alarm_string_not_equal):
			return 'value is "{}", but should be "{}"'.format(detectedValue, config.alarm_string_not_equal)
		if config.alarm_value_equal and (locale.atof(detectedValue) == float(config.alarm_value_equal)):
			return 'value is {}'.format(detectedValue)
		if config.alarm_value_not_equal and (locale.atof(detectedValue) != float(config.alarm_value_not_equal)):
			return 'value is {}, but should be {}'.format(detectedValue, config.alarm_value_not_equal)
		if config.alarm_value_more_than and locale.atof(detectedValue) > float(config.alarm_value_more_than):
			return 'value is {}, but should not exceed {}'.format(locale.atof(detectedValue), config.alarm_value_more_than)
		if config.alarm_value_less_than and locale.atof(detectedValue) < float(config.alarm_value_less_than):
			return 'value is {}, but should be greater than {}'.format(locale.atof(detectedValue), config.alarm_value_less_than)

	def sendMail(self, s, error):
		if s.smtphost:
			logging.info("Sending alarm email to %s via %s", s.mailto, s.smtphost)
		else:
			logging.info("Sending alarm email to %s using local smtp", s.mailto)

		# Create main message
		msg = MIMEMultipart()
		msg['Subject'] = EMAIL_SUBJECT_TPL.format(self.hostname, s.name)
		if s.mailfrom:
			m_from = s.mailfrom
		else:
			m_from = s.username + "@" + s.hostname
		msg['From'] = m_from
		msg['To'] = ', '.join(s.mailto)
		msg.preamble = 'This is a multi-part message in MIME format.'

		# Add base text
		body = EMAIL_MESSAGE_TPL.format(
			s.name,
			self.hostname,
			time.strftime("%a, %d %b %Y %H:%M:%S"),
			error
		)
		txt = MIMEText(body)
		msg.attach(txt)

		# Send the message
		if s.smtpssl and s.smtphost:
			smtp = smtplib.SMTP_SSL(s.smtphost, timeout=300)
		else:
			smtp = smtplib.SMTP(timeout=300)

		if s.smtphost:
			smtp.connect(s.smtphost)
		else:
			smtp.connect()
		if s.smtpuser or s.smtppass:
			smtp.login(s.smtpuser, s.smtppass)
		smtp.sendmail(m_from, s.mailto, msg.as_string())
		smtp.quit()

	def executeAlarmCommand(self, s, error):
		cmdToRun = s.alarmCommand
		cmdToRun = cmdToRun.replace('%%CHECKNAME%%', s.name)
		cmdToRun = cmdToRun.replace('%%HOSTNAME%%', self.hostname)
		cmdToRun = cmdToRun.replace('%%DATETIME%%', time.strftime("%a, %d %b %Y %H:%M:%S"))
		cmdToRun = cmdToRun.replace('%%ERROR%%', error)

		logging.debug("Executing alarm command %s", cmdToRun)

		ret = subprocess.run(cmdToRun, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		if ret.stderr:
			self._log.info('{} subprocess stderr:\n{}', cmdToRun, ret.stderr.decode())
		if ret.stdout:
			stdout = ret.stdout.decode()
			self._log.debug('{} subprocess stdout:\n{}', cmdToRun, stdout)
		if ret.returncode != 0:
			self._log.error('subprocess {} exited with error code {}'.format(cmdToRun, ret.returncode))



class Settings:
	''' Represents settings for a check '''

	EMAIL_LIST_SEP = ','

	def __init__(self, name, config):
		self.config = config
		self.hostname = socket.getfqdn()
		self.username = getpass.getuser()

		## Check name
		self.name = name
		## Disabled
		self.disabled = self.getBoolean(name, 'DISABLED', False)
		## Email server connection data
		self.smtphost = self.getStr(name, 'SMTPHOST', None)
		self.smtpuser = self.getStr(name, 'SMTPUSER', None)
		self.smtppass = self.getStr(name, 'SMTPPASS', None)
		self.smtpssl = self.getBoolean(name, 'SMTPSSL', False)
		## List of email address to notify in case of alarms (disabled if missing)
		mailtoList = self.getStr(name, 'MAILTO', None)
		if mailtoList:
			self.mailto = [ x.strip() for x in mailtoList.strip().split(self.EMAIL_LIST_SEP) ]
		else:
			self.mailto = None
		## Command to execute in case of alarms (disabled if missing)
		self.alarmCommand = self.getStr(name, 'ALARM_COMMAND', None)
		## Sender address for the notification email
		self.mailfrom = self.getStr(name, 'MAILFROM', getpass.getuser()+'@'+socket.gethostname())
		## Values to compare
		self.alarm_string_equal = self.getStr(name, 'ALARM_STRING_EQUAL', None)
		self.alarm_string_not_equal = self.getStr(name, 'ALARM_STRING_NOT_EQUAL', None)
		self.alarm_value_equal = self.getStr(name, 'ALARM_VALUE_EQUAL', None)
		self.alarm_value_not_equal = self.getStr(name, 'ALARM_VALUE_NOT_EQUAL', None)
		self.alarm_value_more_than = self.getStr(name, 'ALARM_VALUE_MORE_THAN', None)
		self.alarm_value_less_than = self.getStr(name, 'ALARM_VALUE_LESS_THAN', None)
		## Command to obtain the value for comparation
		self.command = self.getStr(name, 'COMMAND', None)
		## Regexp to extract value from command output (default to match full string)
		self.regexp = self.getStr(name, 'REGEXP', '(.*)')

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
	parser.add_argument('-d', '--dry-run', action='store_true', help="do not send emails or execute completion script")
	args = parser.parse_args()

	if args.quiet:
		level = logging.WARNING
	else:
		level = logging.INFO
	logging.basicConfig(level=level)

	try:
		main = Main(args.configFile)
		main.run(args.dry_run)
	except Exception as e:
		logging.critical(traceback.format_exc())
		print('ERROR: {}'.format(e))
		sys.exit(1)

	sys.exit(0)
