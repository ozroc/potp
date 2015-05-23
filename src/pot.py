#!/usr/bin/env python

# Python Object Transfer
#

import ssl
import json
import uuid
import socket
import logging

import protocols
import transport

_DEB = logging.debug

#
# Common errors
#

class InvalidMessageFormat(Exception):
    def __init__(self, given_format='unknown'):
        self.__bad_format = given_format
    def __str__(self):
        return 'Message should be a dict but "%s" given.' & self.__bad_format

class MissingMessageKey(Exception):
    def __init__(self, missing_key='unknown'):
        self.__missing_key = missing_key
    def __str__(self):
        return 'The following key "%s" is missing in the message.' & self.__missing_key

class AnonymousMessage(Exception):
    def __str__(self):
        return 'Message is from anonymous.'

class InvalidResponseToRequest(Exception):
    def __init__(self, cause='unknown cause'):
        self.__cause = cause
    def __str__(self):
        return 'Invalid response from remote endpoint (%s)'

class RequestedHandlerNotFound(Exception):
    def __init__(self, id='unknown'):
        self.__req_id = id
    def __str__(self):
        return  'Handler with id="%s" not registered in endpoint.' % self.__req_id

class NoDefaultHandlerRegistered(Exception):
    def __str__(self):
        return 'Endpoint cannot run in server mode because no handler is registered.'
    
class CannotUnregisterDefaultHandler(Exception):
    def __str__(self):
        return 'Default handler cannot be unregister, change default handler first.'
    
class CannotEncodeURI(Exception):
    def __init__(self, uri):
        self.__uri = uri
    def __str__(self):
        return 'Cannot decode "%s" as POTP URI' % self.__uri

class EndpointNotConnected(Exception):
    def __str__(self):
        return 'Endpoint is disconnected, connect first.'

_ERROR = {
    'missing key': { 'error': True, 'exception': MissingMessageKey() },
    'anonymous not allowed': { 'error': True, 'exception': AnonymousMessage() },
    'unknown destination': { 'error': True, 'exception': RequestedHandlerNotFound() },
    'no error': { 'error': False },
    'handler exception': { 'error': True, 'exception': None }
    }

class Endpoint(object):
    """ This is a POT endpoint.
    You can connect to other endpoint and send/receive from him. """
    
    def __init__(self, qos={}):
        self.__protocol = protocols.get_protocol(qos)
        self.__transport = transport.get_transport(qos)
        self.__transport.bind(self._dispatcher_)
        self.__request_handler = {}
        self.__default_handler = None

        self.__allow_anonymous = True
        self.__anonymous = False

        self.__run_as_server = False
        self.__dest_handler = None
        self.__id = str(uuid.uuid4())
        _DEB('Endpoint "%s" created' % self.__id)

    @property
    def uri(self):
        return 'potp://%s' % self.__transport.sap
    
    @property
    def server_enabled(self):
        return self.__transport.server_mode

    @property
    def client_enabled(self):
        return self.__transport.client_mode

    def register_request_handler(self, request_handler, id=None):
        id = str(uuid.uuid4()) if (id is None) else id
        _DEB('Register handler: %s' % id)
        # First request handler is the default
        self.__request_handler[id] = request_handler
        if self.__default_handler is None:
            self.set_default_handler(id)

    def set_default_handler(self, id):
        if id not in self.__request_handler.keys():
            raise RequestedHandlerNotFound(id)
        _DEB('Set default handler: %s' % id)
        self.__default_handler = id

    def unregister_handler(self, id):
        if id not in self.__request_handler.keys():
            raise RequestedHandlerNotFound(id)
        if self.__default_handler == id:
            raise CannotUnregisterDefaultHandler()
        _DEB('Unregister handler: %s')
        del(self.__request_handler[id])

    def stop_serving(self):
        _DEB('Shutdown received')
        self.__run_as_server = False

    def server_loop(self, sap=None):
        _DEB('Starting server loop')
        if self.__default_handler is None:
            raise NoDefaultHandlerRegistered()
        if sap is None:
            sap = self.__transport.create_sap()
        _DEB('Server SAP: %s' % sap)
        self.__transport.open(sap)
        self.__run_as_server = True        
        while self.__run_as_server:
            pass
        self.__transport.close()

    def connect(self, uri):
        _DEB('Endpoint wants to connect to: %s' % uri)
        if not isinstance(uri, str):
            raise CannotEncodeURI(uri)
        if not uri.startswith('potp://'):
            raise CannotEncodeURI(uri)
        uri = uri[7:]
        if '/' in uri:
            sap = uri.split('/')[0]
            self.__dest_handler = uri[uri.index('/') + 1:]
        else:
            sap = uri
            self.__dest_handler = None
        sap = transport.encode_SAP(sap)
        _DEB('Client SAP: %s' % sap)
        self.__transport.connect(sap)

    def disconnect(self):
        _DEB('Endpoint wants to disconnect')
        self.__transport.disconnect()
        self.__dest_handler = None

    def __marshall__(self, to_send):
        return self.__protocol.marshall(to_send)
    
    def __unmarshall__(self, received):
        return self.__protocol.unmarshall(received)

    # It is synchronous
    def _dispatcher_(self, request):
        request = self.__unmarshall__(request)
        try:
            self.__check_message_request__(request)
        except MissingMessageKey:
            return self.__marshall__(_ERROR['missing key'])
        except AnonymousMessage:
            if not self.__allow_anonymous:
                return self.__marshall__(_ERROR['anonymous not allowed'])
            
        src = request.get('src', None)

        if request['dest'] is None:
            dest = self.__default_handler
        else:
            dest = request['dest']
            if dest not in self.__request_handler.keys():
                return self.__marshall__(_ERROR['unknown destination'])

        # Create reply
        reply = { 'dest': src,
                  'src': dest }
        # Callback
        try:
            reply.update({'ret': self.__request_handler[dest](request['req'])})
            reply.update(_ERROR['no error'])            
        except Exception, e:
            reply.update(_ERROR['handler exception'])
            reply.update({'exception': e})
        # Return
        return self.__marshall__(reply)

    def __basic_checks__(self, message):
        if not isinstance(message, dict):
            raise InvalidMessageFormat(type(message))
        if 'src' not in message.keys():
            raise AnonymousMessage()
        
    def __check_message_request__(self, message):
        self.__basic_checks__(message)
        if 'req' not in message.keys():
            raise MissingMessageKey('req')
        if 'dest' not in message.keys():
            raise MissingMessageKey('dest')
        
    def __check_message_reply__(self, message):
        self.__basic_checks__(message)
        if 'ret' not in message.keys():
            raise MissingMessageKey('ret')
        if 'error' not in message.keys():
            raise MissingMessageKey('error')
    
    def request(self, request):
        if not self.client_enabled:
            raise EndpointNotConnected()

        # Convert to dict
        request = { 'req': request }
        request.update({'src': (None if self.__anonymous else self.__id)})
        request.update({'dest': self.__dest_handler})

        reply = self.__transport.send_request(self.__marshall__(request))
        reply = self.__unmarshall__(reply)

        # Client raises exception to upper levels
        try:
            self.__check_message_reply__(reply)
        except AnnonymousMessage:
            if not self.__allow_anonymous:
                raise AnnonymousMessage()
            reply.update({'dest': self.__id})
            
        if self.__id != reply['dest']:
            # Response is for other request
            pass

        if reply['error']:
            if 'exception' not in reply.keys():
                raise MissingMessageKey('exception')
            raise reply['exception']

        ### Source is: response.get('src', None), is it needed? ###
        return reply['ret']
