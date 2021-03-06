#!/usr/bin/env python

import json
import os
import sys
import pprint
import requests
import requests.packages.urllib3
from auth import CredentialStore
from errors import CredentialError

requests.packages.urllib3.disable_warnings()
pp = pprint.PrettyPrinter(indent=4)

class CredStore(object):
    def __init__(self, *args, **kwargs):
        credential_file = kwargs.pop("credential_file", None)
        self.credential_store = CredentialStore(credential_file=credential_file)

        self.credential_profile_name = kwargs.pop("profile", None)
        self.credentials = self.credential_store.get_credentials(self.credential_profile_name)

try:
    my_creds = CredStore(profile='default')
except CredentialError, e:
    print e
    sys.exit()

api_key,conn_id = my_creds.credentials.api_key, my_creds.credentials.conn_id
token = "%s/%s" % (api_key, conn_id)

url = my_creds.credentials.cbd_api_url

if not url.lower().startswith('https://'):
	print "cbd_api_url in the credentials file must begin with 'https://'"
	sys.exit(1)

#dict to track the distinct hashes that match the process name in question
#  powershell.exe is this script
hashes = {}

# A dict to map hashes back to application names
appNames = {}


# Create our results directory if it does not exist
if not os.path.exists('./results'):
    os.makedirs('./results')

#Request up to 1000 events with an application name of powershell.exe
uri = '%s/integrationServices/v3/event?applicationName=powershell.exe&rows=1000&searchWindow=2w' % (url)
headers = {'X-Auth-Token': token}
r = requests.get(uri, headers=headers)
foo = r.json()


print uri
print "Powershell Hashes and Count of Events with that Hash as the App SHA"

# Iterate over the results 
for bar in foo['results']:
	#Get the eventId for each result
	eid = bar['eventId']
	
	# use the eventId as part of a filename
	fn = "./results/%s.applicationName" % (eid)

	# write the contents of this event to the file
	#  can compare these files to the files/events we generate when we query for the sha256hash below
	#  Writing individual "results" files because we can grep the assorted out files looking for the hash

	with open(fn, 'w') as wr:
		wr.write(json.dumps(bar, indent=2))

	# Assign the hash of the application to a variable
	sha256Hash = bar['selectedApp']['sha256Hash']
	
	# Check to see if the hash is in our hash dict
	if sha256Hash in hashes.keys():
		# If yes, increment the count
		hashes[sha256Hash] += 1
	else:
		# If no, create an entry and set the count to 1
		hashes[sha256Hash] = 1

# Print the hashes and the count of times we saw the hash tied to 'powershell.exe'
#  This will show us the various versions of powershell we have running
for k in hashes.keys():
	print k + " = " + str(hashes[k])


# Reiterate over the hash dictionary
#  search the events in Cb Defense  for events generated by a process with each hash
for j in hashes.keys():
	print "#" * 100
	
	#build a URL based upon sha56hash=hash_from_hash_dict
	# MY ASSERTION IS THAT THIS QUERY RETURNS THE MOST RECENT x EVENTS WHEN rows=x
	# INSTEAD OF THE x MOST RECENT EVENTS THAT HAVE sha256hash AS THE APP SHA256
	uri = '%s/integrationServices/v3/event?sha256hash=%s&rows=10000&searchWindow=2w' % (url, j)
	r = requests.get(uri, headers=headers)
	foo = r.json()

	print ""
	print "Application Names and Count of Occurrences"
	print uri
	
	# for each result returned for the sha256 based search
	for bar in foo['results']:
		#assign the eventId to a variable
		eid = bar['eventId']
		
		# Use the eventId as part of a filename in a subdirectory of this directory
		fo = './results/%s.sha256hash' % (eid)
		
		#  Writing individual "results" files because we can grep the assorted output files looking for the hash
		with open(fo, 'w') as results:
			#write the contents of the event to its own file
			results.write(json.dumps(bar, indent=2))
		
		#  look to see if the hash of the returned process is in our dictionary of hashes
		if bar['selectedApp']['sha256Hash'] in hashes.keys():
			# grab the application name
			appName = bar['selectedApp']['applicationName']
			
			#  if the applicationName is in our dictionary of application names, increment count by 1
			if appName in appNames.keys():
				appNames[appName] +=1
			else:
				# if not create an new entry with a count of 1
				appNames[appName] = 1
	
	print j
	for k in appNames.keys():
		# print the name of the process and how many times we have seen that hash executed as that name
		print "    " + k + " = " + str(appNames[k])


