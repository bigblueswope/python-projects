#!/bin/env python
import datetime, sys, pprint, cbapi, requests
from cli_parser_turner import build_cli_parser

requests.packages.urllib3.disable_warnings() 
    
def parent_search(args, pdoc):
    
    args.query = "hostname: %s process_name: %s process_pid: %d" % (pdoc['hostname'], pdoc['parent_name'], pdoc['parent_pid'])
    
    # build a cbapi object
    cb = cbapi.CbApi(args.url, token=args.token, ssl_verify=args.ssl_verify)

    # use the cbapi object to iterate over all matching process documents
    try:
        r = cb.process_search(args.query)
        identifier = r['results'][0]['id']
        seg_id = r['results'][0]['segment_id']
    except:
        return False

    try:
        events = cb.process_events(identifier, seg_id)
        for cpe in events['process']['childproc_complete']:
            cpe_split = cpe.split('|',)
            if int(cpe_split[4]) == pdoc['process_pid'] and cpe_split[5] == 'false':
                process_end_time = datetime.datetime.strptime(cpe_split[0], "%Y-%m-%d %H:%M:%S.%f")
                return process_end_time
    except:
        return False
    return False

    
def main():
    args = build_cli_parser()
    args.query = 'start:-186m hostname:TBS-H35XLYVPUF2 username:ampierce -process_name:chrome.exe'
    #args.query = 'start:-186m hostname:TBS-H35XLYVPUF2 username:TURNER\\ampierce'
    print "Initial Query: %s", args.query
    # build a cbapi object
    cb = cbapi.CbApi(args.url, token=args.token, ssl_verify=args.ssl_verify)
    source_set = cb.process_search(args.query)
    if source_set['total_results'] > 1500:
        print "Total Results: %d" % source_set['total_results']
        print "More than 1500 results to parse, exiting script to spare your CB server."
        sys.exit(0)

    # use the cbapi object to iterate over all matching process documents
    answer = cb.process_search_iter(args.query)
    count = 0 
    lrcount = 0
    # iterate over each process document in the results set
    for pdoc in answer:
        count += 1
        # Query the parent process to see if this child process has ended and assign the end date to process_end_time
        process_end_time = parent_search(args, pdoc)
        
        if process_end_time:
            end = process_end_time
        else:
            end = datetime.datetime.strptime(pdoc['last_update'], "%Y-%m-%dT%H:%M:%S.%fZ")
       
        # Start time
        try:
            start = datetime.datetime.strptime(pdoc['start'], "%Y-%m-%dT%H:%M:%S.%fZ")
        except:
            pass

        # Difference betweeen the process end time and process start time
        runtime = int((end - start).seconds)
        
        # Change the compared value if 60 seconds is not considered a long run of powershell
        if runtime > 60:
            lrcount += 1
            print "#########################"
            print "Proc Doc: %s/#/analyze/%s/%d" % (args.url, pdoc['id'], pdoc['segment_id'])
            print "Hostname: ", pdoc['hostname']
            print "Username: ", pdoc['username']
            print "Process Name: ", pdoc['process_name']
            print "Command Line: ", pdoc['cmdline']
            print "Runtime: %d seconds" % runtime
            print "Process start  : %s" % start
            print "Process endtime: %s" % process_end_time
            print "$$$$$$$$$$$$$$$$$$$$$$$$$"
    print "Matching Process Count: ", count
    print "Matching Long Running Process Count: ", lrcount
    
if __name__ == "__main__":
    sys.exit(main())
