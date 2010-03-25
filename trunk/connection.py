import Queue
import logging as log

from webSocket import *

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
        #Whether we're accepting commands from the connection at the moment
        self.Throttled = False

    #Return True if Recv() operation returns a list (possibly empty),
    #otherwise return False to indicate the Connection is no longer valid and should be terminated
    def RecvCommands(self):
        commands = self.WebSocket.Recv()

        #Terminate connection if commands is None
        if commands == None:
            return False
        elif not self.Throttled:
            for command in commands:
                self._PutToQueue(self.ReadQueue, command)

            self.CommandsReceived += len(commands)

        return True

    def GetNextCommand(self):
        return self._GetFromQueue(self.ReadQueue)

    def SendCommand(self, command):
        return self._PutToQueue(self.WriteQueue, command, "Connection queuing command to send: %s")

    def _SendCommand(self, command):
        log.info("Connection sending command: %s" % (repr(command)))
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
                log.info(logMsg % (repr(item)))
                
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

    #Needed for use with select()
    def fileno(self):
        return self.WebSocket.fileno()
