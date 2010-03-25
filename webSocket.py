import socket
import logging as log

HANDSHAKE = '''
HTTP/1.1 101 Web Socket Protocol Handshake\r
Upgrade: WebSocket\r
Connection: Upgrade\r
WebSocket-Origin: %s\r
WebSocket-Location: ws://%s\r
WebSocket-Protocol: sample
'''.strip() + '\r\n\r\n'

STARTBYTE = '\x00'
ENDBYTE = '\xff'

class WebSocket:
    def __init__(self, socket):
        self.Socket = socket
        self.WebSocketBuffer = ''
        self.ApplicationPath = '/'
        self.Host = None
        self.Origin = None
        
        try:
            httpHeader = self.Socket.recv(4096)
            log.info(httpHeader)
            self.ParseHttpHeader(httpHeader)
            
            if self.Origin != None and self.Host != None:
                #WebSocket-Origin = Origin parameter of HTTP request
                #WebSocket-Location = Host parameter of HTTP request
                handshake = HANDSHAKE % (self.Origin, self.Host + self.ApplicationPath)
                log.info("WebSocket sending handshake to client")
                self.Socket.send(handshake)
                log.info("WebSocket sent handshake:\r\n%s" % (handshake) )
            else:
                log.info("WebSocket could not parse HTTP header")
                raise Exception("WebSocket could not parse HTTP header")
        except Exception:
            log.info("WebSocket could not complete the HTTP handshake to establish a web socket connection")
            self.Close()
            raise Exception("WebSocket could not complete the HTTP handshake to establish a web socket connection")

    def ParseHttpHeader(self, header):
        appNameStartIndex = header.find("GET /")
        if appNameStartIndex != -1:
            appNameEndIndex = header.find(" HTTP/1.")
            
            if appNameEndIndex != -1:
                appPath = header[appNameStartIndex + 4:appNameEndIndex]
                self.ApplicationPath = appPath
                log.info("Application Path requested by WebSocket connection: %s" % (appPath))

        hostStartIndex = header.find("Host: ")
        if hostStartIndex != -1:
            hostEndIndex = header.find("\r", hostStartIndex)
            if hostEndIndex != -1:
                host = header[hostStartIndex + 6 : hostEndIndex]
                self.Host = host
                log.info("Host requested by WebSocket connection: %s" % (host))

        originStartIndex = header.find("Origin: ")
        if originStartIndex != -1:
            originEndIndex = header.find("\r", originStartIndex)
            if originEndIndex != -1:
                origin = header[originStartIndex + 8 : originEndIndex]
                self.Origin = origin
                log.info("Origin requested by WebSocket connection: %s" % (origin))

    def Send(self, msg):
        log.info(u'WebSocket sending data to client: %s' % (repr(msg)))
        self.Socket.send(STARTBYTE + str(msg) + ENDBYTE)

    #Will return a (possibly empty) list of commands,
    #or None if the connection is suspected to be closed or an error occurs
    def Recv(self):

        webSocketCommands = []
        
        try:
            log.info('WebSocket waiting to receive data from client')
            data = self.Socket.recv(4096)

            if not data:
                raise Exception("WebSocket client connection closed")

            #Buffer incoming data
            self.WebSocketBuffer += data
            
            #Parse as many commands as we can from the data we've received, based on web socket protocol
            bufferIndex = self.WebSocketBuffer.find(ENDBYTE)
            while bufferIndex != -1:
                command = self.WebSocketBuffer[:bufferIndex+1]
                
                #will become '' if index+1 is out of range
                self.WebSocketBuffer = self.WebSocketBuffer[bufferIndex+1:]

                if command.find(STARTBYTE) == 0:
                    #strip protocol bytes from front and end of string
                    command = command[1:-1]
                    webSocketCommands.append(command)
                    log.info(u'WebSocket got command from client: %s' % (repr(command)))
                else:
                    log.info(u'WebSocket got incorrectly formatted data from client: %s' % (repr(command)))

                bufferIndex = self.WebSocketBuffer.find(ENDBYTE)

            log.info('WebSocket got data from client: %s' % (repr(webSocketCommands)))
            return webSocketCommands
        
        except Exception as ex:
            log.info("WebSocket got an exception while trying to receive from client socket")
            return None

    def Close(self):
        log.info('WebSocket closing client socket')
        self.Socket.close()

    #Needed for use with select()
    def fileno(self):
        return self.Socket.fileno()
        
