#!/usr/bin/env python

import sys
import logging
logging.basicConfig(level=logging.DEBUG)
import threading

sys.path.append('../src/')
import pot

server = pot.Endpoint()
client = pot.Endpoint()

def process_request(request):
    print 'Echo: %s' % request
    return request

server.register_request_handler(process_request)
server_thread = threading.Thread(target=server.server_loop)
server_thread.start()

print 'Wait for server becames ready...'
while not server.server_enabled:
    pass

print 'Server listening in "%s"' % server.uri
client.connect(server.uri)

reply = client.request({})
print 'Reply: %s' % reply

client.disconnect()
server.stop_serving()
server_thread.join()
