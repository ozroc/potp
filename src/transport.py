#!/usr/bin/env python
#
# Python Object Transfer: transport
#

import struct
import select
import socket
import logging
import threading
import SocketServer

_DEB = logging.debug
_INF = logging.info

_VMTU = 1024

#
# Interface classes
#

class TransportSAP(object):
    """ This class is used to store transport configuration. """
    def __str__(self):
        """ String representation should be enought to create more
        instances. """
        return "none"

    
class Transport(object):
    """ This class send and receive "frames" of data. """

    @property
    def secure(self):
        """ Secure transport.

        This property returns if transport is secure or not. """
        return False

    
    @property
    def sap(self):
        """ Service access point.

        This property is used to compose endpoint string reference. """
        return TransportSAP()


    @property
    def ready(self):
        """ On line.

        This property returns if transport is ready or not. """
        return False

    
    @property
    def is_bind(self):
        """ Return if transport has a callback or not.

        Args:
            none.

        Returns:
            True if callback is defined.

        Raises:
            none.
        """
        raise NotImplementedError()

    
    def bind(self, callback):
        """ Set server callback.

        Args:
            callback: handler for received requests from remote clients.

        Returns:
            none.

        Raises:
            none.
        """
        raise NotImplementedError()


    def open(self, local_sap):
        """ Open local SAP.

        Create local service access point to allow remote
        endpoints to connect and transfer data.

        Args:
            local_resource: a local resource used as SAP.

        Returns:
            none

        Raises:
            CannotOpenTransport: unable to open local resource.
        """
        raise NotImplementedError()


    def close(self):
        """ Close local SAP.

        Close local service access point and forbids remote
        endpoints to connect.

        Args:
            none

        Returns:
            none

        Raises:
            CannotCloseTransport: unable to close local resource.
        """
        raise NotImplementedError()
        
    
    def connect(self, remote_sap):
        """ Open remote SAP.

        Connect to remote SAP to transfer data.

        Args:
            remote_resource: a remote resource used as SAP.

        Returns:
            none

        Raises:
            CannotOpenTransport: unable to open resource.
        """
        raise NotImplementedError()

    
    def disconnect(self):
        """ Close remote SAP.

        Close remote service access point.

        Args:
            none

        Returns:
            none

        Raises:
            CannotCloseTransport: unable to close remote resource.
        """
        raise NotImplementedError()

    
    def send_request(self, msg):
        """ Send request.

        Args:
            msg: request to send.

        Returns:
            response to request from server.

        Raises:
            ConnectionLost: error writing socket.
        """
        raise NotImplementedError()


#
# Common errors
#

class TransportNotConnected(Exception):
    def __init__(self, transport):
        self.__transport = transport
    def __str__(self):
        return '[%s] is not connected yet!' % self.__transport


class TransportError(Exception):
    def __init__(self, cause='unknown'):
        self.__cause = cause
    def __str__(self):
        return 'Error in transport (%s)' % self.__cause


#
# Aux. methods
#

def __get_free_tcp4_port__():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def __wait_frame__(active_socket):
    _INF('Waiting for frame')
    frame_size = active_socket.recv(4)
    if len(frame_size) != 4:
        raise TransportError('Frame header must have 4 bytes')
    frame_size = struct.unpack('i', frame_size)[0]
    data = ''
    total_received = 0
    while total_received < frame_size:
        partial = active_socket.recv(min(_VMTU,
                                         frame_size - total_received))
        if not partial:
            break
        total_received += len(partial)
        data += partial
    _INF('Readed frame of %s bytes' % len(data))
    return data


def __send_frame__(active_socket, data):
    _INF('Sending frame of %s bytes' % len(data))
    header = struct.pack('i', len(data))
    frame = header + data
    sent = active_socket.sendall(frame)
    _INF('Frame sended')


#
# TCP implementation
#

class TCPTransport(Transport):
    class _RequestHandler(SocketServer.StreamRequestHandler):
        def __init__(self, request, client_address, server):
            SocketServer.BaseRequestHandler.__init__(self,
                                                     request,
                                                     client_address,
                                                     server)

        def handle(self):
            while True:
                r, w, x = select.select([self.request], [], [])
                if not r:
                    break
                _DEB('Server waiting for frames...')
                try:
                    request = __wait_frame__(self.request)
                except TransportError:
                    _INF('Server disconnected from client')
                    break
                _DEB('Server received "%s"' % repr(request))
                response = self.server.request_handler(request)
                _DEB('Server sends "%s"' % repr(response))
                __send_frame__(self.request,
                               '' if response is None else response)
            
    class _TCPBasicServer(SocketServer.ThreadingMixIn,
                         SocketServer.TCPServer):
        def __init__(self, address, request_handler):
            SocketServer.TCPServer.__init__(self,
                                            address, request_handler)
            self.callback = None

        def request_handler(self, request):
            if self.callback is None:
                return
            return self.callback(request)
        
    def __init__(self):
        Transport.__init__(self)
        self.__local = None
        self.__remote = None

        self.__client_socket = None

        self.__server = None
        self.__server_thread = None
        self.__request_callback = None

    @property
    def client_mode(self):
        return self.__client_socket is not None

    @property
    def server_mode(self):
        return self.__server is not None
    
    @property
    def ready(self):
        return self.__local or self.__remote

    @property
    def sap(self):
        return self.__local

    @property
    def is_binded(self):
        if self.__server is None:
            return False
        return self.__server.callback is not None
    
    def bind(self, callback):
        self.__request_callback = callback        
        if self.__server is None:
            return
        self.__server.callback = callback
    
    def open(self, local_sap):
        assert(isinstance(local_sap, TCPSAP))
        _DEB('Create server socket...')
        self.__local = local_sap
        self.__server = self._TCPBasicServer(
            (self.__local.address, self.__local.port),
            self._RequestHandler)
        _DEB('Server created in %s:%s' % self.__server.server_address)
        self.__server_thread = threading.Thread(
            target = self.__server.serve_forever)
        self.__server_thread.daemon=True
        self.__server_thread.start()
        # If bind() is called before open()
        if self.__request_callback is not None:
            self.bind(self.__request_callback)            
        
    def close(self):
        _DEB('Terminate server socket...')
        self.__server.shutdown()
        self.__server_thread.join()
        self.__server = None
        self.__server_thread = None
        self.__local = None
        
    def connect(self, remote_sap):
        assert(isinstance(remote_sap, TCPSAP))
        _DEB('Client wants to connect to %s' % remote_sap)
        self.__remote = remote_sap
        self.__client_socket = socket.socket(socket.AF_INET,
                                             socket.SOCK_STREAM)
        self.__client_socket.connect((self.__remote.address,
                                      self.__remote.port))
        _DEB('Connected to server')
        
    def disconnect(self):
        _DEB('Terminate client socket...')
        self.__remote = None
        try:
            self.__client_socket.shutdown(socket.SHUT_RDWR)
            self.__client_socket.close()
        finally:
            self.__client_socket = None

    def send_request(self, request):
        _DEB('Client wants to send "%s"' % repr(request))
        if not self.client_mode:
            raise TransportNotConnected(self)
        __send_frame__(self.__client_socket, request)
        _DEB('Client wait for response...')
        response = __wait_frame__(self.__client_socket)
        _DEB('Client received "%s"' % repr(response))
        return response

            
class TCPSAP(TransportSAP):
    def __init__(self, address='0.0.0.0', port=None):
        self.__address = address
        self.__port = (port if port in [None, 0]
                       else __get_free_tcp4_port__())

    @property
    def address(self):
        return self.__address

    @property
    def port(self):
        return self.__port

    def __str__(self):
        return 'tcp@%s:%s' % (self.__address, self.__port)
