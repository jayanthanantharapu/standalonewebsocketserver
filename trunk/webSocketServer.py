#!/usr/bin/env python

import sys
import time
import socket
import threading
import Queue
import ConfigParser
import logging as log

from connection import *
from connectionManager import *

log.basicConfig(level=log.DEBUG, stream=sys.stderr)

#Dynamically instantiate an instance of an Application-derived class from a module
#The module must provide an Instantiate() method
def InstantiateApplication(moduleName, *classArgs):
    module = __import__(moduleName)
    classInstance = module.Instantiate(*classArgs)
    log.info( repr(classInstance) )
    return classInstance
    
#
#MAIN
#
if __name__ == "__main__":
    log.info('Loading configuration info')
    config = ConfigParser.ConfigParser()
    config.read('config.txt')
    port = config.getint('Server', 'Port')
    connectionQueueSize = config.getint('Server', 'ConnectionQueueSize')

    #Start applications
    log.info('Loading Applications...')
    applications = {}

    #Admin app
    adminApp = InstantiateApplication('AdminApplication', 'admin')
    applications['/'] = adminApp
    adminAppThread = threading.Thread(target=adminApp.Run).start()
    
    #Dynamically load applications specified in config.txt
    applicationList = config.items('Applications')
    for application in applicationList:
        appModuleName = application[1]
        appInstanceName = application[0]
        log.info('\tLoading instance of application %s as %s' % (appModuleName, appInstanceName))
        applicationInstance = InstantiateApplication(appModuleName, appInstanceName)
        applications['/' + appInstanceName] = applicationInstance
        applicationThread = threading.Thread(target=applicationInstance.Run).start()

    log.info("Applications Loaded:")
    log.info(repr(applications))
    
    #done with config    
    del config
    
    log.info('Starting web socket server')
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind( ('', port) )
    serverSocket.listen(connectionQueueSize)
    del port
    del connectionQueueSize

    #Start connection manager
    connectionManager = ConnectionManager()
    connectionManagerThread = threading.Thread(target=connectionManager.Run).start()

    #Accept clients
    try:
        while 1:
            log.info('Waiting to accept client connection...')
            clientSocket, clientAddress = serverSocket.accept()

            log.info('Got client connection')
            connection = Connection(clientSocket, clientAddress)

            if connection.ApplicationPath in applications:
                if applications[connection.ApplicationPath].AddClient(connection) == True:                
                    connectionManager.AddConnection(connection)
                else:
                    connection.Close()
                    connection = None
            else:
                log.info("Client requested an unknown Application. Closing connection.")
                connection.Close()
                connection = None
            
    except Exception as ex:
        log.info('Server encountered an unhandled exception.')
        log.info(repr(ex))

    log.info('Web socket server closing.')


    
