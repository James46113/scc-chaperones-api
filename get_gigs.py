import requests
import json
import pprint
import datetime
import re

res = requests.get("https://sccspreadsheetapi-production.up.railway.app/get_gigs/0")
gigs = [gig for gig in json.loads(res.text) if gig['date'] and gig['time'] and gig['voices'] != 'Clerks']


for gig in gigs:
    gig['date'] = datetime.datetime.strptime(gig['date'].split("T")[0], "%Y-%m-%d")
    time_str = gig['time']
    match = re.match(r'(\d{1,2})\.(\d{2})(am|pm)', time_str)
    if match:
        hour, minute, ampm = int(match.group(1)), int(match.group(2)), match.group(3)
        if ampm == 'pm' and hour != 12:
            hour += 12
        if ampm == 'am' and hour == 12:
            hour = 0
        gig['date'] = gig['date'].replace(hour=hour, minute=minute)

pprint.pprint(gigs)
print(gigs[1]['date'])