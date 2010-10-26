#!/usr/bin/python

import cherrypy
import lg_authority

#lg_authority.tool.register_as('auth')

#Test that register_as works as expected
#@cherrypy.config(**{'auth.groups': ['auth']})
@cherrypy.config(**{'tools.lg_authority.groups': ['auth']})
class TestAlias(object):
    #We could mount this separately,  but embedded does more interesting
    #things with config.
    auth = lg_authority.AuthRoot()

    @cherrypy.expose
    def index(self):
        return "You're logged in as {user}!".format(user=cherrypy.user.name)

    @cherrypy.expose
    @lg_authority.groups('None')
    def deny(self):
        return "You can't see this or else you're cheating!"

    @cherrypy.expose
    @lg_authority.groups('any')
    def public(self):
        return "Anyone can see this!"

cherrypy.tree.mount(TestAlias(), '/')
cherrypy.config.update({ 
    'server.socket_host': '0.0.0.0'
    , 'server.socket_port': 8080
    , 'tools.lg_authority.on': True
    , 'tools.lg_authority.site_debug': True
    , 'tools.lg_authority.site_storage': 'mongodb'
    , 'tools.lg_authority.site_storage_conf': {
        'db': 'test'
        ,'collection_base': 'test'
        }
    , 'tools.lg_authority.site_registration_recaptcha': {
        'public': '6Le8H74SAAAAABOZXhtQr9Ld3WrWn1bnEyp19JFC'
        ,'private': '6Le8H74SAAAAAMHdM9B_8bmvFvkJbFqn3Y6WYcwD'
        }
    })
try:
    from site_local import *
except ImportError:
    pass

cherrypy.engine.start()
cherrypy.engine.block()

