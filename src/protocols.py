#!/usr/bin/env python

import pyckle

# Python Object Transfer: protocols

DEFAULT=PIP

class NotSerializable(Exception):
    def __init__(self, bad_object):
        self.__bo = bad_object
    def __str__(self):
        return 'Object not serializable: "%s"' % str(self.__bo)

    
class NotInstantiable(Exception):
    def __str__(self):
        return 'String not instantiable.'
    

class Protocol(object):
    """ This class handles how to transfer and object as an string and
    how to create some object described in a string. """
    
    @staticmethod
    def marshall(serializable_object):
        """ Converts some object into a "stream" format.

        This function is used to "convert" some Python object
        into a string, ready to send over some protocol.

        Args:
            serializable_object: object to convert.

        Returns:
            string buffer with the object representation.

        Raises:
            NotSerializable: some objects cannot be converted to a string.
        """
        raise NotImplementedError()
    
    @staticmethod
    def unmarshall(object_representation):
        """ Return the object instance given by the representation.

        This function is used to "instance" some Python object
        from a string, readed from some stream.

        Args:
            object_representation: string used in the object instance.

        Returns:
            instantiated object.

        Raises:
            NotInstantiable: string cannot be decoded as an object.
        """
        raise NotImplementedError()
    

class PIP(Protocol):
    """ This protocol uses python-standard "pickle" module """
    def marshall(serializable_object):
        try:
            return pickle.dumps(serializable_object)
        except:
            raise NotSerializable(serializable_object)

    def unmarshall(object_representation):
        try:
            return pickle.loads(object_representation)
        except:
            raise NotInstantiable()
        
