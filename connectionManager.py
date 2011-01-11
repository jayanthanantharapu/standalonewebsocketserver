import select
##Copyright (c) 2010 Colin Zablocki
##
##Permission is hereby granted, free of charge, to any person obtaining a copy
##of this software and associated documentation files (the "Software"), to deal
##in the Software without restriction, including without limitation the rights
##to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
##copies of the Software, and to permit persons to whom the Software is
##furnished to do so, subject to the following conditions:
##
##The above copyright notice and this permission notice shall be included in
##all copies or substantial portions of the Software.
##
##THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
##THE SOFTWARE.

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
