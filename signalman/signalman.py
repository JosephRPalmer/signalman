#!/usr/bin/env python3
"""
signalman takes an endpoint and either a http code and/or a response text element and continues running until a timeout elapses (with error 1) or the conditions are met (exit code 0)
"""

__author__ = "Joseph Ryan-Palmer"
__version__ = "0.1.17"
__license__ = "MIT"

import argparse
import requests
import sys
import time

from interruptingcow import timeout
from retrying import retry


class Timeout(Exception):
    pass


class ResponseError(Exception):
    def __init__(self, message="Request response did not match required response"):
        self.message = message
        super().__init__(self.message)


def timedprint(message):
    print("{} -- {}".format(time.strftime("%H:%M:%S", time.localtime()), message))


def urlbuilder(url, port, ssl):
    scheme = "http"
    colon = ":"

    if ssl or port == 443:
        scheme = "https"
    elif not port:
        port = "80"

    if "://" in str(url):
        schema_array = url.split("://", 1)
        url = schema_array[1]
        timedprint(
            "Detected '{}://'. Removing protocol scheme and rebuilding URL.".format(schema_array[0]))

    if "/" in url:
        fqdn = url.split("/", 1)[0]
        path = url.split("/", 1)[1]
    else:
        fqdn = url
        path = ""

    if ":" in fqdn:
        colon = ""
        port = ""
        timedprint("Ignoring --port directive as port found in URL")

    urlbuilder = "{}://{}{}{}/{}".format(scheme, fqdn, colon, port, path)

    timedprint("Using built url {}".format(urlbuilder))

    return urlbuilder


@retry(wait_exponential_multiplier=1000, wait_exponential_max=10000)
def caller(url, return_type, return_value, headers, debug):

    resp = requests.get(url, headers=headers)

    if debug:
        timedprint("Sent: {}".format(resp.request.headers))
        timedprint("Recieved: Headers:{} Body:{}".format(
            resp.headers, str(resp.content)))

    if return_type == "code":
        if int(resp.status_code) != int(return_value):
            timedprint("Response code was {}, looking for {}".format(
                resp.status_code, code))
            raise ResponseError()
        else:
            timedprint("Response code conditions met, found {}".format(
                resp.status_code))
    elif return_type == "text":
        if return_value not in resp.text:
            timedprint("Response text did not contain {}".format(text))
            raise ResponseError()
        else:
            timedprint(
                "Response text conditions met, found {} in response text".format(text))
    elif return_type == "json":
        json_key = return_value.split(":", 1)[0]
        json_value = return_value.split(":", 1)[1]

        if json_key in resp.json():
            if str(resp.json()[json_key]) == str(json_value):
                timedprint("Response JSON contains matching key and value. Found '{}:{}'".format(
                    json_key, resp.json()[json_key]))
            else:
                timedprint("Response JSON contains matching key but wrong value. Value found is {}, looking for {}.".format(
                    str(resp.json()[json_key]), str(json_value)))
                raise ResponseError()
        else:
            timedprint("Response key/value pair not matched. Retrying...")
            raise ResponseError()


def header_format(headers):

    headerlist = []

    if " " in str(headers):
        headerlist = headers.split(" ")
    else:
        headerlist = headers

    outputheaders = {}

    for header in headerlist:
        if header.count(":") < 1:
            print("Header with detail {} was skipped due to incompatible formatting".format(
                header))
            continue
        templist = header.split(":")
        outputheaders[templist[0]] = templist[1]
        timedprint("Adding header '{}:{}'".format(templist[0], templist[1]))

    return outputheaders


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--timeout", type=int,
                        help='Set timeout for signalman to run in minutes', required=True)

    parser.add_argument("--endpoint", type=str,
                        help='Endpoint to poll', required=True)
    parser.add_argument("--port", type=int, help='Port to poll')

    parser.add_argument(
        "--r-type", type=str, help='Set a return type for signalman to look for, choose from text, code and json',
        choices=["json", "code", "text"], required=True)

    parser.add_argument("--r-value", type=str,
                        help='Set a return value for signalman to look for', required=True)

    parser.add_argument("--headers", type=str, nargs='+',
                        help='Set request headers to use, for example to request Content-Type: application/json use content-type:application/json')

    parser.add_argument('--ssl', action='store_true',
                        help="Use to poll with https enabled")
    parser.add_argument('--debug', action='store_true',
                        help="Use to enable debugging")

    # Specify output of "--version"
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s (version {version})".format(version=__version__))

    args = parser.parse_args()

    headers = {}

    if args.headers:
        headers = header_format(args.headers)

    try:
        with timeout(args.timeout*60, exception=TimeoutError):
            caller(urlbuilder(args.endpoint, args.port, args.ssl), args.r_type,
                   args.r_value, headers, args.debug)
    except TimeoutError:
        print("signalman timed out")
        sys.exit(1)


if __name__ == '__main__':
    """ This is executed when run from the command line """
    main()
