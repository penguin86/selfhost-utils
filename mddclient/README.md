# MDDCLIENT
It's a client for dynamic DNS services like Infomaniak's.
Like [ddclient](https://github.com/ddclient/ddclient), but supports sending multiple updates for different domains.
I developed this because [Infomaniak's DynDns APIS](https://www.infomaniak.com/en/support/faq/2376/dyndns-updating-a-dynamic-dns-via-the-api) doesn't support multiple domains updates on the same call. So, even if ddclient was supported for a single domain, it was needed to setup multiple instances to update multiple domains (or subdomains) on the same machine.

## Compatibility
I wrote this to solve the multiple domain update problem on Infomainak, but should work for every other provider supporting the original ddclient.

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
Edit `/usr/local/etc/mddclient.cfg` setting up the server url, username, password and the main domain to update. If you have other domains or subdomains running on the same fiber/dsl, configure them in the subsections as shown in the config example.
Run `/usr/local/bin/mddclient.py /usr/local/etc/mddclient.cfg` to check it is working.
Now copy the cron file:
```
cp mddclient.cron.example /etc/cron.d/mddclient
```
For increased safety, edit the cron file placing your email address in MAILTO var to be notified in case of mddclient.py catastrophic failure.

Setup is now complete: the cron runs the script every minute and updates the dns.

## Optimization
If multiple subdomains are served from the same public url (the same fiber/DSL account) it is possible to optimize the domain updates: when the main one results already up-to-date, the others are not updated. This feature is enabled by default, but can be disabled setting OPTIMIZE_API_CALLS to false in the config.
