#!/usr/bin/python

import cherrypy
import lg_authority

lg_authority.tool.register_as('auth')

cherrypy.tree.mount(lg_authority.AuthRoot(), '/auth')
cherrypy.config.update({ 
    'server.socket_host': '0.0.0.0'
    , 'server.socket_port': 8081 
    , 'tools.lg_authority.on': True
    , 'tools.sessions.on': True
    })
cherrypy.engine.start()
cherrypy.engine.block()

