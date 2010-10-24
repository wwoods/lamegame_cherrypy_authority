#!/usr/bin/python

import cherrypy
import lg_authority

lg_authority.tool.register_as('auth')

#Test that register_as works as expected
@cherrypy.config(**{'auth.groups': ['auth']})
class TestAlias(object):
    #We could mount this separately,  but embedded does more interesting
    #things with config.
    auth = lg_authority.AuthRoot()

    @cherrypy.expose
    def index(self):
        return "You must be logged in to see this, {user.name}!".format(user=cherrypy.user)

    @cherrypy.expose
    @lg_authority.groups('None')
    def deny(self):
        return "You can't see this or else you're cheating!"

cherrypy.tree.mount(TestAlias(), '/')
cherrypy.config.update({ 
    'server.socket_host': '0.0.0.0'
    , 'server.socket_port': 8081 
    , 'tools.lg_authority.on': True
    , 'tools.lg_authority.site_debug': True
    , 'tools.lg_authority.site_storage': 'mongodb'
    , 'tools.lg_authority.site_storage_conf': {
        'db': 'test'
        ,'collection_base': 'test'
        }
    })
cherrypy.engine.start()
cherrypy.engine.block()

