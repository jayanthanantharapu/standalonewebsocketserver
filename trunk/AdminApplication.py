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

from application import *
from connection import *

import time
import datetime


def Instantiate(appName='admin'):
    adminApp = AdminApplication(appName)
    return adminApp

class AdminApplication(Application):
    def __init__(self, name='admin'):
        Application.__init__(self, name)

        self.CommandMap["startApp"] = self.StartApp
        self.CommandMap["stopApp"] = self.StopApp
        self.CommandMap["getStats"] = self.GetStats

    def Run(self):
        log.info("AdminApplication now running.")

        Application.Run(self)

        log.info("AdminApplication DONE running.")

    def StartApp(self):
        pass

    def StopApp(self):
        pass

    def GetStats(self):
        pass
