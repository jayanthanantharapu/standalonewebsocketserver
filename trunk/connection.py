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

import Queue
import time
import logging as log

from webSocket import *

class DummyConnection:
    def __init__(self):
        self.Connected = True
        self.Throttled = False

  #allow sending async notification of commands to observers
    def Subscribe(self, listenerCallback):
        pass

    def Unsubscribe(self, listenerCallback):
        pass

    def NotifyCommandReceived(self, command):
        pass
        
    #Return True if Recv() operation returns a list (possibly empty),
    #otherwise return False to indicate the Connection is no longer valid and should be terminated
    def RecvCommands(self):
        return True

    def GetNextCommand(self):
        return None

    def SendCommand(self, command):
        pass

    def SendCommands(self):
        pass

    def Close(self):
        self.Connected = False

    def CheckTimeout(self):
        pass

    def ResetTimeout(self):
        pass

    #Pass None for timeoutSecs to have no timeout
    def SetTimeout(self, timeoutSecs):
        pass


class Connection:
    def __init__(self, clientSocket, clientAddress):
        self.CommandsReceived = 0
        self.CommandsSent = 0
        
        self.ClientAddress = clientAddress
        self.WebSocket = WebSocket(clientSocket)
        self.ApplicationPath = self.WebSocket.ApplicationPath

        self.ReadQueue = Queue.Queue(0)
        self.WriteQueue = Queue.Queue(0)

        self.Connected = True

        #Used for managing connections that should timeout after periods of inactivity
        self._Timeout = None
        self._LastTime = None
        
        #Whether we're accepting commands from the connection at the moment
        self.Throttled = False

        self.Listeners = []

    #allow sending async notification of commands to observers
    def Subscribe(self, listenerCallback):
        self.Listeners.append(listenerCallback)

    def Unsubscribe(self, listenerCallback):
        self.Listeners.remove(listenerCallback)

    def NotifyCommandReceived(self, command):
        for listenerCallback in self.Listeners:
            listenerCallback(command)       
        

    #Return True if Recv() operation returns a list (possibly empty),
    #otherwise return False to indicate the Connection is no longer valid and should be terminated
    def RecvCommands(self):
        commands = self.WebSocket.Recv()

        #Terminate connection if commands is None
        if commands == None:
            return False
        else:
            if not self.Throttled:
                for command in commands:
                    log.debug("Connection Queued a command %s" % command)
                    self._PutToQueue(self.ReadQueue, command)

                numberCommandsReceived = len(commands)
                if numberCommandsReceived > 0:
                    self.CommandsReceived += numberCommandsReceived
                    self.ResetTimeout()

        return True

    def GetNextCommand(self):
        command = self._GetFromQueue(self.ReadQueue)
        
        if command != None:
            log.debug("GetNextCommand() : %s" % (command))
        return command

    def SendCommand(self, command):
        return self._PutToQueue(self.WriteQueue, command, "Connection queuing command to send: %s")

    def _SendCommand(self, command):
        log.debug("Connection sending command: %s" % (repr(command)))
        self.WebSocket.Send(command)
        self.CommandsSent += 1

    def SendCommands(self):
        command = self._GetFromQueue(self.WriteQueue)
        while not command == None:
            self._SendCommand(command)
            command = self._GetFromQueue(self.WriteQueue)

    def Close(self):
        self.Connected = False
        self.WebSocket.Close()

    def _PutToQueue(self, queue, item, logMsg=None):
        if not queue.full():
            if not logMsg == None:
                log.debug(logMsg % (repr(item)))
                
            try:
                queue.put_nowait(item)
            except Queue.Full:
                return False
            
            return True
        else:
            return False

    def _GetFromQueue(self, queue, logMsg=None):
        if not queue.empty():
            try:
                return queue.get_nowait()
            except Queue.Empty:
                return None
        else:
            return None

    def CheckTimeout(self):
        if self._Timeout != None:
            currentTime = time.time()
            
            if currentTime - self._LastTime >= self._Timeout:
                self.Close()

    def ResetTimeout(self):
        self._LastTime = time.time()

    #Pass None for timeoutSecs to have no timeout
    def SetTimeout(self, timeoutSecs):
        if timeoutSecs > 0 or timeoutSecs == None:
            self._Timeout = timeoutSecs
            self.ResetTimeout()

    #Needed for use with select()
    def fileno(self):
        return self.WebSocket.fileno()
