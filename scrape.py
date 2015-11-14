#!/usr/bin/env python
""" periscope scraper. Lots borrowed from pyriscope. """

import re
import requests
import simplejson as json
import sys
import argparse
import os
import io
from multiprocessing import Pool, freeze_support
from functools import partial
from pubnub import Pubnub


PERISCOPE_GETBROADCAST = "https://api.periscope.tv/api/v2/getBroadcastPublic?{}={}"
PERISCOPE_GETACCESS = "https://api.periscope.tv/api/v2/getAccessPublic?{}={}"
DEFAULT_UA = "Mozilla\/5.0 (Windows NT 6.1; WOW64) AppleWebKit\/537.36 (KHTML, like Gecko) Chrome\/45.0.2454.101 Safari\/537.36"
URL_PATTERN = re.compile(r'(http://|https://|)(www.|)(periscope.tv)/(w|\S+)/(\S+)')
CHUNK_PATTERN = re.compile(r'chunk_\d+\.ts')


def dissect_url(url):
    match = re.search(URL_PATTERN, url)
    parts = {}

    try:
        parts['url'] = match.group(0)
        parts['website'] = match.group(3)
        parts['username'] = match.group(4)
        parts['token'] = match.group(5)

        if len(parts['token']) < 15:
            parts['broadcast_id'] = parts['token']
            parts['token'] = ""

    except:
        print "\nError: Invalid URL: {}".format(url)
        sys.exit(1)

    return parts


def get_mocked_user_agent():
    try:
        response = requests.get("http://api.useragent.io/")
        response = json.loads(response.text)
        return response['ua']
    except:
        try:
            response = requests.get("http://labs.wis.nu/ua/")
            response = json.loads(response.text)
            return response['ua']
        except:
            return DEFAULT_UA


def download_chunk(params, req_headers=None):
    path = params['path']
    with open(path, 'wb') as handle:
        data = requests.get(params['url'], stream=True, headers=req_headers)

        if not data.ok:
            print("\nError: Unable to download chunk.")
            sys.exit(1)
        for block in data.iter_content(4096):
            handle.write(block)


def grab_all_pubnub_messages(pubnub, channel):
    results = []
    start_time = None

    while True:
        print "grabbing at ", start_time
        result = pubnub.history(
            channel,
            count=100,
            start=start_time,
            reverse=True)
        if result and len(result) == 3 and len(result[0]) > 0:
            msgs = result[0]
            start = result[1]
            end = result[2]
            start_time = end
            results += msgs
            print "read %d messages" %(len(msgs))
        else:
            break

    return results


def grab_pubnub_data(subkey, authkey, channel):
    try: 
        pubnub = Pubnub(
            publish_key='demo',
            subscribe_key=subkey,
            auth_key=authkey)

        results = grab_all_pubnub_messages(pubnub, channel)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception, e:
        print "Exception grabbing pubnub: ", e
        raise

    return results



#
#
#
#
#
#
if __name__ == "__main__":
    freeze_support()

    # argument parser
    parser = argparse.ArgumentParser(description='extract periscope links')
    parser.add_argument('inputs', help='input json files')
    parser.add_argument('output_path', help='output path')
    parser.add_argument(
        '--procs',
        help='number of download processes',
        default=4)
    args = parser.parse_args()


    with open(args.inputs, "r") as f:
        url_list = f.readlines()
        url_count = len(url_list)



    for url in url_list:
        url_parts = dissect_url(url)

        print url_parts

        if url_parts['token'] == "":
            req_url = PERISCOPE_GETBROADCAST.format("broadcast_id", url_parts['broadcast_id'])
        else:
            req_url = PERISCOPE_GETBROADCAST.format("token", url_parts['token'])

        # grab headers
        req_headers = {} 
        req_headers['User-Agent'] = DEFAULT_UA

        # download stream info
        try:
            response = requests.get(req_url, headers=req_headers)
            broadcast_public = json.loads(response.text)

            print json.dumps(broadcast_public, indent=4)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            continue

        if 'success' in broadcast_public and broadcast_public['success'] == False:
            print "\nError: Video expired/deleted/wasn't found: {}".format(url_parts['url'])
            continue

        # grab metadata
        scope_id = broadcast_public['broadcast']['id']
        scope_user_id = broadcast_public['broadcast']['user_id']

        # create directory
        stream_path = os.path.join(args.output_path, scope_id)
        if not os.path.exists(stream_path):
            os.makedirs(stream_path)

        # save broadcast data
        broadcast_filepath = os.path.join(stream_path, "pub_broadcast.json")
        try:
            with io.open(broadcast_filepath, "w", encoding="utf-8") as bc_file:
                bc_file.write(response.text + "\n")
        except (KeyboardInterrupt, SystemExit):
            raise            
        except:
            print "Couldn't write file \"%s\"" %( broadcast_filepath)
            raise


        if broadcast_public['broadcast']['state'] == 'RUNNING':
            # do nothing for now
            print "active broadcasts not supported"

        else:
            if not broadcast_public['broadcast']['available_for_replay']:
                print "\nError: Replay unavailable: {}".format(url_parts['url'])
                continue

            # Broadcast replay is available.
            if url_parts['token'] == "":
                req_url = PERISCOPE_GETACCESS.format("broadcast_id", url_parts['broadcast_id'])
            else:
                req_url = PERISCOPE_GETACCESS.format("token", url_parts['token'])

            try:
                response = requests.get(req_url, headers=req_headers)
                access_public = json.loads(response.text)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                print "Couldn't get access!"
                continue

            access_response_path = os.path.join(stream_path, "access_resp.json")
            try:
                with open(access_response_path, "w") as ar_file:
                    ar_file.write(response.text + "\n")
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                print "Couldn't write access response file \"%s\"" % (
                    access_response_path)

            # make sure ok
            if 'success' in access_public and access_public['success'] == False:
                print "\nError: Video expired/deleted/wasn't found: {}".format(url_parts['url'])
                continue

            #
            # download chunk data
            #


            base_url = access_public['replay_url'][:-14]

            req_headers['Cookie'] = "{}={};{}={};{}={}".format(access_public['cookies'][0]['Name'],
                                                               access_public['cookies'][0]['Value'],
                                                               access_public['cookies'][1]['Name'],
                                                               access_public['cookies'][1]['Value'],
                                                               access_public['cookies'][2]['Name'],
                                                               access_public['cookies'][2]['Value'])
            req_headers['Host'] = "replay.periscope.tv"

            response = requests.get(access_public['replay_url'], headers=req_headers)
            chunks = response.text

            # make our directory
            stream_data_path = os.path.join(stream_path, "stream")
            if not os.path.exists(stream_data_path):
                os.makedirs(stream_data_path)

            download_list = []
            for chunk in re.findall(CHUNK_PATTERN, chunks):
                download_list.append(
                    {
                        'url': "{}/{}".format(base_url, chunk),
                        'path': os.path.join(stream_data_path, chunk)
                    }
                )


            # start our downloads
            """
            mpool = Pool(processes=args.procs)
            dl_partial = partial(download_chunk, req_headers=req_headers)
            mpool.map(dl_partial, download_list )

            mpool.close()
            mpool.join()
            mpool = None
            """

            # grab pubnub data
            pn_subkey = access_public['subscriber']
            pn_authkey = access_public['auth_token']
            pn_channel = access_public['channel']

            print "grabbing pubnub data"

            try:
                results = grab_pubnub_data(pn_subkey, pn_authkey, pn_channel)

                # save results
                chat_path = os.path.join(stream_path, "pn_chat.json")
                with open(chat_path, "w") as chat_file:
                    for msg in results:
                        chat_file.write(json.dumps(msg)+"\n")
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, e:
                print "Expcetion grabbing / writing pubnub data: ", e
                continue


        #if url_parts['token'] == "":


        # Set a mocked user agent.
        #if agent_mocking:
        #    stdout("Getting mocked User-Agent.")
        #    req_headers['User-Agent'] = get_mocked_user_agent()
        #else:
        #    req_headers['User-Agent'] = DEFAULT_UA

