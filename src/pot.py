#!/usr/bin/env python

# Python Object Transfer
#

import ssl
import json
import socket

import protocols

class Endpoint(object):
    """ This is a POT endpoint.
    You can connect to other endpoint and send/receive from him. """
    
    def __init__(self, protocol=protocols.DEFAULT):
        self.__protocol = protocol

        
    def __marshall__(self, to_send):
        return self.__protocol.marshall(to_send)

    
    def __unmarshall__(self, received):
        return self.__protocol.unmarshall(received)
