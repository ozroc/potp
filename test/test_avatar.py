#!/usr/bin/env python

import sys
import logging
logging.basicConfig(level=logging.DEBUG)
import threading

import potp.avatars
from potp.avatars import avatar_property
from potp import endpoint

# Create example class
class A(potp.avatars.Avatar):
    def __init__(self, value):
        potp.avatars.Avatar.__init__(self)
        self.__val = value

    @avatar_property
    def value(self):
        return self.__val

    def sum(self, value):
        return self.__val + value

    def increment(self, value):
        self.__val = self.value + value

    def divide(self, d):
        return float(self.__val) / float(d)

# Create instance at server
server_object = A(10)

# Create endpoints
server = endpoint.Full()
client = endpoint.Client()

# Connect server_object with server endpoint
server_object.avatar_attach(server)

# Enable server
server_thread = threading.Thread(target=server.server_loop)
server_thread.start()

print 'Wait for server becames ready...'
while not server.server_enabled:
    pass
print 'Server listening in "%s"' % server.uri
print 'Server object: %s' % server_object.avatar_uri

# Connect client to server
client.connect(server_object.avatar_uri)

# Get remote object
client_object = potp.avatars.AvatarProxy(client)
client_object.attach_proxy()

print '@Property:', client_object.value
print 'sum(10):', client_object.sum(10)
client_object.increment(5)
print 'increment(5)'
print '@Property:', client_object.value
try:
    print 'divide(0)', client_object.divide(0)
except ZeroDivisionError:
    print 'It works!'

client.disconnect()
server.stop_serving()
server_thread.join()
