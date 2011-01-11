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


#Dynamically instantiate an instance of an Application-derived class from a module
#The module must provide an Instantiate() method
def InstantiateApplication(moduleName, *classArgs):
    module = __import__(moduleName)
    log.info("InstantiateApplication - Module: " + repr(module))
    classInstance = module.Instantiate(*classArgs)
    log.info( repr(classInstance) )
    return classInstance
    
#
#MAIN
#
if __name__ == "__main__":

    config = ConfigParser.ConfigParser()
    config.read('config.txt')
    port = config.getint('Server', 'Port')
    connectionQueueSize = config.getint('Server', 'ConnectionQueueSize')
    debugLevel = config.get('Server', 'DebugLevel')

    if debugLevel == 'Debug':
        debugLevel = log.DEBUG        
    elif debugLevel == 'Info':
        debugLevel = log.INFO
    elif debugLevel == 'Warning':
        debugLevel = log.WARNING        
    elif debugLevel == 'Error':
        debugLevel = log.ERROR
    else:
        debugLevel = log.NOTSET

    log.basicConfig(level=debugLevel, stream=sys.stderr)        
    log.info('Loaded configuration info from config.txt')

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

            try:
                log.info('Got client connection from %s' % (repr(clientAddress)))
                connection = Connection(clientSocket, clientAddress)

                log.info('Client %s requested %s application' % (repr(clientAddress), connection.ApplicationPath))
                if connection.ApplicationPath in applications:
                    requestedApp = applications[connection.ApplicationPath]
                    log.info('Client %s requested app: %s ' % (repr(clientAddress), repr(requestedApp)))

                    connectionManager.AddConnection(connection)
                    requestedApp.AddPendingClient(connection)
                    connection.SetTimeout(requestedApp.VerifyTimeout)
 
                else:
                    log.info("Client %s requested an unknown Application. Closing connection." % repr(clientAddress))
                    connection.Close()
                    connection = None
                    
            except Exception as ex:
                log.info('Execption occurred while attempting to establish client connection from %s.' % repr(clientAddress))
                log.info(repr(ex))
            
    except Exception as ex:
        log.info('Server encountered an unhandled exception.')
        log.info(repr(ex))

    log.info('Web socket server closing.')


    
