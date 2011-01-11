import select
import time
import Queue
import logging as log

from connection import *

class ConnectionManager:
    def __init__(self):
        self.Connections = []
        self.NewConnectionQueue = Queue.Queue(0)
        self.DeadConnections = []

    def AddConnection(self, connection):
        self.NewConnectionQueue.put(connection)

    def RemoveConnection(self, connection):
        try:
            connectionIndex = self.Connections.index(connection)
            connectionObject = self.Connections.pop(connectionIndex)
            connectionObject.Close()
            log.info("ConnectionManager stopped managing a connection")
            
        except ValueError:
            log.warning("ConnectionManager tried to remove connection that didn't exist")
            pass  

    def Run(self):
        log.info("Connection Manager now running.")
        
        while 1:
            #Manage any new connections
            while not self.NewConnectionQueue.empty():
                log.info("Connection Manager got a new connection to manage.")
                self.Connections.append(self.NewConnectionQueue.get())

            if self.Connections == []:
                 time.sleep(2.0)
            else:
                #Read data from connections that have sent us something
                #If nothing becomes ready within 2 seconds, proceed
                read, write, err = select.select(self.Connections, self.Connections, self.Connections, 2.0)
                
                for connection in read:
                    if not connection.Connected or not connection.RecvCommands():
                        self.DeadConnections.append(connection)
                        
                #Send data to ready connections for which we have data
                for connection in write:
                    connection.SendCommands()
                    connection.CheckTimeout()

                    if not connection.Connected:
                        self.DeadConnections.append(connection)
               
                    
                #Clean up dead connections
                for connection in self.DeadConnections:
                    self.RemoveConnection(connection)

                del self.DeadConnections[:]
