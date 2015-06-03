#!/usr/bin/env python

import uuid
import logging

_DEB = logging.debug

class AvatarPropertyRequiresAvatar(Exception):
    def __str__(self):
        return '@avatar_property is only for Avatar() objects!'

class CannotAttachAvatar(Exception):
    def __init__(self, aid):
        self.__aid = aid
    def __str__(self):
        return 'Cannot get Avatar [%s]' % self.__aid


def avatar_property(prop):
    '''Use @avatar_property instead of @property to get the property
       available to all proxies.'''
    @property
    def wrapper(*args, **kwargs):
        try:
            _DEB('Use %s as property' % prop.__name__)
            if prop.__name__ not in args[0].avatar_properties:
                args[0].avatar_properties.append(prop.__name__)
            return prop(*args, **kwargs)
        except AttributeError:
            raise AvatarPropertyRequiresAvatar()
    return wrapper


class Avatar(object):
    '''Use this class to get your class callable by proxies.'''
    __endpoint = None
    __aid = None
    avatar_members = []
    avatar_properties = []
    def __init__(self):
        self.__aid = str(uuid.uuid4())
        # Get public members
        for member in dir(self):
            try:
                if member.startswith('_'):
                    continue
                if member.startswith('avatar_'):
                    continue
                if member in ['members', 'dispatch_request']:
                    continue
                _DEB('Checking member %s (%s)' % (member,
                                                  getattr(self, member)))
                self.avatar_members.append(member)
            except AttributeError:
                _DEB('Member %s is @property' % member)
                self.avatar_properties.append(member)
                continue
            except AvatarPropertyRequiresAvatar:
                pass

    @property
    def avatar_uri(self):
        '''Get the URI to connect to the object.'''
        return '%s/%s' % (self.__endpoint.uri, self.__aid)
    
    def avatar_attach(self, endpoint):
        '''Connects the object to a Server() endpoint.'''
        _DEB('Attaching [%s] to %s' % (self.__aid, endpoint.uri))
        self.__endpoint = endpoint
        self.__endpoint.register_request_handler(self.__dispatch__,
                                                 self.__aid)
        
    def __dispatch__(self, request):
        if not isinstance(request, dict):
            return None

        # Attach request
        if 'attach' in request.keys():
            _DEB('Proxy request to attach')
            return {
                'members': self.avatar_members,
                'properties': self.avatar_properties }

        # Normal object request
        try:
            member_name = request['member']
            member = getattr(self, member_name)
            ret =  member if not callable(member) else member(
                *request['args'],
                **request['kwargs'])
        except Exception, e:
            _DEB('Exception: %s' % e)
            ret = None
        ret = { 'return': ret }
        _DEB('Proxy request: %s' % member_name)
        if member_name in self.avatar_properties:
            ret.update({ 'property': True })
        return ret


class AvatarProxy(object):
    def __init__(self, endpoint):
        self.__endpoint = endpoint
        self.__pid = str(uuid.uuid4())
        self.__aid = None
        self.__attached = False
        self.__received_property = None
        
    @property
    def attached(self):
        return self.__attached
        
    def attach(self, aid=None):
        self.__aid = aid
        _DEB('Requesting attachment with %s' % self.__aid)
        result = self.__endpoint.request({
            'attach': self.__pid
        }, self.__aid)

        if not result:
            raise CannotAttachAvatar(self.__aid)

        if not isinstance(result, dict):
            raise CannotAttachAvatar(self.__aid)
                
        # Create stubs
        for member in result['members']:
            self.__create_member__(member)
        for prop in result['properties']:
            self.__create_member__(prop, True)
        self.__attached = True

    @property
    def __dispatch_property__(self):
        return self.__received_property
    
    def __create_member__(self, name, is_property=False):
        _DEB('Adding member %s%s...' % (name,
                                        ' (property)' if is_property else ''))
        exec('''%(property)s
def _%(member)s(self, *args, **kwargs):
    ret = self.__dispatch__('%(member)s', *args, **kwargs)
    return ret
setattr(self.__class__, '%(member)s', _%(member)s)
            ''' % {
                'member': name,
                'property': '@property' if is_property else ''
            })

    def __dispatch__(self, op, *args, **kwargs):
        _DEB('Requesting "%s" to [%s]' % (op, self.__aid))
        response = self.__endpoint.request({
            'member': op,
            'args': args,
            'kwargs': kwargs}, self.__aid)
        return response['return']
