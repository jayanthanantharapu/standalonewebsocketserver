from connection import *
import datetime
import traceback
import Queue

#DB imports
#import MySQLdb
import sqlalchemy
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class Application:

    #
    #Constructor
    #
    def __init__(self, name):
        self.Name = name
        self.CreationTime = datetime.datetime.utcnow()
                
        self.LastTime = self.CreationTime
        self.DeltaTime = 0

        self.ConnectionTimeout = None
        self.VerifyTimeout = None

        self.PendingClientsQueue = Queue.Queue(0)        
        self.Clients = []
        self.CommandMap = {}
        #which connection the current command came from
        self.CommandConnectionContext = None


    def AddPendingClient(self, connection):
        #connection.SetTimeout(self.VerifyTimeout or self.ConnectionTimeout)
        self.PendingClientsQueue.put(connection)

    #Return:
    #True = verified
    #False = unverified or disconnected
    #None = no credentials received yet
    def VerifyConnection(self, connection):
        
        credentials = connection.GetNextCommand()
        if not connection.Connected:
            log.info("Application %s: Connection was dropped before it could be verified" % (self.Name))
            return False
        
        elif credentials == None:
            return None
        
        else:
            #Accept any input as credentials
            log.info("Credentials %s" % (credentials))
        
        return True

    #Attempt to verify client. Return True if successful,
    #None if no credentials recevied yet,
    #False otherwise
    def AddClient(self, connection):
        
        verified = self.VerifyConnection(connection)
        if verified == True:
            log.info("Connection from [%s] was verified." % (repr(connection.ClientAddress)))
            self.Clients.append(connection)
            connection.SetTimeout(self.ConnectionTimeout)
            return True
        
        elif verified == None:
            return None
        
        else:
            log.info("Connection from [%s] could not be verified." % (repr(connection.ClientAddress)))
            return False
        
    def RemoveClient(self, connection):
        try:
            clientIndex = self.Clients.index(connection)
            connectionObject = self.Clients.pop(clientIndex)
            #Set Connected to False so the connection manager
            #knows to clean up the connection
            connectionObject.Connected = False
            log.info("Application %s dropped a client" % (self.Name))
            
        except ValueError:
            log.warning("Application %s tried to drop a client that it wasn't servicing" % (self.Name))
            pass

    #attempt to look up the handler for a command and return the result of running that logic
    def ProcessCommand(self, command):
        log.debug('Application %s processing a client command' % (self.Name))
        parts = command.split('|')

        #log.info('  Command map for %s: %s' % (self.Name, repr(self.CommandMap)))
        if parts[0] in self.CommandMap:
            args = parts[1:]
            result = self.CommandMap[parts[0]](*args)
            log.debug('%s client Command %s returned %s' % (self.Name, command, result))
            return result
        else:
            log.debug('%s got an Unknown command %s' % (self.Name, command))
            return None

    def Run(self, callback=None):
        while 1:
            try:
                #main input processing for each client
                client = None
                for client in self.Clients:
                    self.CommandConnectionContext = None
                    
                    if client.Connected == True:
                        self.CommandConnectionContext = client
                        receivedCommand = client.GetNextCommand()            

                        if receivedCommand != None:
                            commandResult = self.ProcessCommand(receivedCommand)

                            if commandResult != None:
                                client.SendCommand(commandResult)
                    else:
                        self.RemoveClient(client)

                #################################
                #Call any custom callback logic
                #################################
                if not callback == None:
                    callback()

                #
                #Verify and add any pending clients
                #
                pendingConnectionsToReAdd = []    
                while not self.PendingClientsQueue.empty():
                    pending = self.PendingClientsQueue.get()

                    #If failed to verify client, or they disconnected, result will be False
                    #If no credentials received yet, result will be None
                    #Otherwise client passed verification and result will be True
                    #Re-add pending connection to the queue only if no credentials were received yet and
                    #they haven't timed out or disconnected
                    addClientResult = self.AddClient(pending)
                    if addClientResult == None:
                        pendingConnectionsToReAdd.append(pending)
                    
                #Re-add pending connections that should be tested again later
                for pending in pendingConnectionsToReAdd:
                    self.AddPendingClient(pending)
                    
            except Exception as ex:
                self.CommandConnectionContext = None
                if client != None:
                    self.RemoveClient(client)
                    
                log.error('Application got an exception:')
                log.error(repr(ex))
                traceback.print_exc()

