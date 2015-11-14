#!/usr/bin/env python
"""Pull periscope text and links from twitter json files."""

import simplejson as json
import argparse
import codecs
import glob
import re


parser = argparse.ArgumentParser(description='extract periscope links')
parser.add_argument('inputs', help='input json files')
parser.add_argument('output', help='output filename')
parser.add_argument(
    '-e', '--encoding', default="utf-8",
    help="json file encoding (default is utf-8)")

args = parser.parse_args()

file_list = sorted(glob.glob(args.inputs))
file_count = len(file_list)

# regex
periscope_regex = re.compile(r"periscope\.tv", re.I)

#
# step through each file
#

for filename_index in range(file_count):

    filename = file_list[filename_index]
    print "opening \"%s\" (%d of %d)" % (
        filename,  filename_index+1, file_count)

    with open(filename, "r") as f:

        # tweets are expected on each line
        for rawline in f:

            # check for empty lines
            rawline = rawline.strip()
            if not rawline:
                continue

            line = codecs.decode(rawline, args.encoding)

            # convert it to json
            try:
                tweet = None
                tweet = json.loads(line)

            except Exception, e:
                print "failed to parse json: ", e
                print line

            # continue if the tweet failed
            if tweet is None:
                continue

            # see if this is a gnip info message, and skip if it is
            if 'info' in tweet and 'message' in tweet['info']:
                # print "info tweet", repr(tweet)
                continue

            # make sure it's a tweet
            if not 'text' in tweet or not 'created_at' in tweet or not 'user' in tweet:
                print "line is not a recognized tweet..."
                print "> ", line
                print "----------"
                continue

            # check to see if it's been processed, if not, add it to set
            tweet_id = tweet['id']
            tweet_text = tweet['text']

            urls = tweet['entities']['urls']

            for url in urls:
                # print url["expanded_url"]
                expanded_url = url["expanded_url"]
                #print periscope_regex.search(expanded_url), expanded_url
                if periscope_regex.search(expanded_url) is not None:
                    print "%d,%s,\"%s\"" % (
                        tweet_id,
                        expanded_url.replace("\"", "\"\""),
                        tweet_text)



