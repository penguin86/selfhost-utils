# Selfhost utilities
A collection of utilities for self hosters.
Every utility is in a folder with its relevant configuration and is completely separated from the other, so you can install only the ones you need.

## HEALTHCHECK
A simple server health check.
Sends an email and/or executes a command in case of alarm (high temperature, RAID disk failed etc...).
As an example, the command may be a ntfy call to obtain a notification on a mobile phone or desktop computer.
Meant to be run with a cron (see healthcheck.cron.example).
Tested on Debian 11, but should run on almost any standard linux box.

![Email](images/healthcheck_email_notification.png)      ![Ntfy](images/healthcheck_ntfy_notification.png)

Please see [healthcheck documentation](healthcheck/README.md)

# License
This whole repository is released under GNU General Public License version 3: see http://www.gnu.org/licenses/
