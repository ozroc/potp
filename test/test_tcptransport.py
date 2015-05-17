#!/usr/bin/env python

import sys
import logging
logging.basicConfig(level=logging.DEBUG)

sys.path.append('../src/')
import transport

sap = transport.TCPSAP('localhost', 10500)

server = transport.TCPTransport()
client = transport.TCPTransport()

def process_request(request):
    print 'Echo: %s' % request
    return request

server.open(sap)
server.bind(process_request)

client.connect(sap)

client.send_request('test string')
client.send_request('another request')

client.disconnect()
server.close()
