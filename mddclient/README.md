# 🖥 MDDCLIENT
It's a client for `dyndns2` protocol: it is used to interact with dynamic DNS services like Dyn or Infomaniak's.
Updates the IP assigned for a domain, allows the use of dynamic ip internet access (commin in residential contexts like DSL, Fiber, 5G...) for hosting services.
Like [ddclient](https://github.com/ddclient/ddclient), but updates multiple domaing with multiple REST calls.

I developed this because [Infomaniak's DynDns APIS](https://www.infomaniak.com/en/support/faq/2376/dyndns-updating-a-dynamic-dns-via-the-api) doesn't support multiple domains updates on the same call. So, even if ddclient was supported for a single domain, in case of multiple (sub)domains it was needed to setup multiple instances to update them all on the same machine.

## Compatibility
Works for any provider supporting `dyndns2` protocol. Was implemented following (this documentation)[https://help.dyn.com/remote-access-api/].
I wrote this to solve the multiple domain update problem on Infomainak.

## Use case
Let's say we have our Nextcloud instance on `https://mysite.cloud`. As self hosters, we run this instance on our server at home, behind our fiber or DSL provider with a dynamic IP. We need to use ddclient to keep the dynamic DNS updated, so the requests to `https://mysite.cloud` are sent to our current IP, that may change in any moment.
Now we decide to host a Matrix chat instance on `https://matrix.mysite.cloud` and a Mastodon social instance on `https://mastodon.mysite.cloud`. We configure ddclient adding the new subdomains in `/etc/ddclient.conf`, but the requests begin to fail with a 400 http code. This happens because our Dynamic DNS provider doesn't support multiple updates on the same request.

So we need a script that issues an update request for every (sub)domain. This is mddclient.

## Setup
Copy the script and the config file into the system to check:
```
cp mddclient.py /usr/local/bin/mddclient.py
cp mddclient.cfg.example /usr/local/etc/mddclient.cfg
```
Make the script executable:
```
chmod +x /usr/local/bin/mddclient.py
```
Edit `/usr/local/etc/mddclient.cfg` setting up the server url, username, password and the domains to update. If you have multiple domains or subdomains running on the same fiber/dsl, configure them, one for subsection as shown in the config example.
Run `/usr/local/bin/mddclient.py /usr/local/etc/mddclient.cfg` to check it is working.
Now copy the cron file (it runs mddclient every 5 minutes):
```
cp mddclient.cron.example /etc/cron.d/mddclient
```
For increased safety, edit the cron file placing your email address in MAILTO var to be notified in case of mddclient.py catastrophic failure.

Setup is now complete: the cron runs the script every five minutes and updates the dns.

## Check status
Some status informations are available with the -s flag:
```
root@myhost# /usr/local/bin/mddclient.py /usr/local/etc/mddclient.cfg -s

lastRun: 2022-05-31 10:40:17.006371
lastRunSuccess: True
lastUpdate: 2022-05-31 10:23:38.510386
lastIpAddr: 151.41.52.133
```

## Optimization
As the update requests are subject to rate limit, the script checks the current IP against Dyn's checkip tool and updates only when necessary. To force an update, use the -f flag.

## Thanks
Thanks to `dyndns.org` for the (checkip)[https://help.dyn.com/remote-access-api/checkip-tool/] tool returning current public IP address.
