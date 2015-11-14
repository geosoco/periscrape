#!/usr/bin/env python
"""Merge multiple files and deduplicate the links."""

import simplejson as json
import argparse
import codecs
import glob
import csv
import re
import io
from csv_unicode import UnicodeReader, UnicodeWriter


parser = argparse.ArgumentParser(description='extract periscope links')
parser.add_argument('inputs', help='input json files')
parser.add_argument('output', help='output filename')
parser.add_argument(
    '-e', '--encoding', default="utf-8",
    help="json file encoding (default is utf-8)")

args = parser.parse_args()

file_list = sorted(glob.glob(args.inputs))
file_count = len(file_list)

url_dict = {}

#
# step through each file
#

for filename_index in range(file_count):
    filename = file_list[filename_index]
    print "opening \"%s\" (%d of %d)" % (
        filename,  filename_index+1, file_count)

    with io.open(filename, "r", encoding="utf-8") as f:
        input_csv = csv.DictReader(codecs.iterencode(f, "utf-8"))

        for row in input_csv:
            url = row['url']
            if url not in url_dict:
                url_dict[url] = row


with io.open(args.output, "w", encoding="utf-8") as outfile:
    outfile.write(u"id,url,text\n")
    for row in url_dict.values():
        tweet_id = row["id"]
        url = row["url"]
        text = row["text"]
        if text is not None:
            text = text.replace("\"", "\"\"")
        else:
            continue

        #print tweet_id, url, text
        #print ':'.join(x.encode('hex') for x in text)
        line = u"%s,%s,\"%s\"\n" % (
            tweet_id.decode("utf-8"),
            url.decode("utf-8"),
            text.decode("utf-8"))
        
        outfile.write(url.decode("utf-8") + "\n")

