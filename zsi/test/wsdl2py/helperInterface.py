#!/usr/local/bin/python
############################################################################
# Joshua Boverhof<JRBoverhof@lbl.gov>, LBNL
# Monte Goode <MMGoode@lbl.gov>, LBNL
# David Robertson <DWRobertson@lbl.gov>, LBNL
# See Copyright for copyright notice!
###########################################################################
import sys
import ZSI
from ZSI.wsdl2python import WriteServiceModule
from ZSI.wstools import WSDLTools

"""
helperInterface

A class for automatically generating client interface code from a wsdl
definition, and a set of classes representing element declarations and
type definitions.  This will produce three files in the current working 
directory named after the wsdl definition name.

eg. <definition name='SampleService'>
    SampleService_services.py
    SampleService_services_types.py
    SampleService_services_interface.py

"""


class WriteHLSModule:
    """Delegates to WriteServiceModule to generate service and types
       files.  Then generates a higher-level interface file.
    """
    def __init__(self, wsdl):
        self.wsdl = wsdl

    def write(self):
        """Locator
              SERVICENAME + ServiceLocator
                  get + PORTNAME

           Binding name 
              GoogleSearchBinding
                 GoogleSearchBindingSOAP
                     GoogleSearchBindingSOAPHLS
        """
        #Write out _services and _types modules
        wsm = WriteServiceModule(self.wsdl)
        wsm.write()

        #Write out interface module
        f_types, f_services = wsm.get_module_names()
        module_name = '%s_%s' %(f_services, 'interface')
        fd = open('%s.py' %module_name, 'w+')
        header = '%s \n# %s.py \n# generated by %s \n# \n# \n%s\n\n'\
          %('#'*50, module_name, self.__module__, '#'*50)
        fd.write(header)
        fd.write('from %s import *\n\n\n' % f_services)

        #WRITE OUT LOCATORS
        portList = []
        for service in wsm._wa.getServicesList():

            for port in service.getPortList():
                hasSoapAddress = False
                soapAddress    = None

                for e in port.getExtensions():
                    if isinstance(e,
                              ZSI.wsdlInterface.ZSISoapAddressAdapter):
                        hasSoapAddress = True
                        soapAddress = e

                if not hasSoapAddress:
                    continue
                portList.append(port)
                portTypeName = port.getBinding().getPortType().getName()

                fd.write('class %sHLocator(%sLocator):\n' % (portTypeName, service.getName()))
                fd.write('    def get%s(self, portAddress=None, **kw):\n' % \
                        portTypeName )
                fd.write('        return %sSOAPHLS(portAddress or %sLocator.%s_address, **kw)\n\n' %  \
                    (port.getBinding().getName(), service.getName(), portTypeName))
                fd.write('    def getPortType(self, portTypeName, **kw):\n')
                fd.write('        for name, fun in self.__class__.__dict__.items():\n')
                fd.write('            if name.endswith(portTypeName):\n')
                fd.write('                return fun(None, **kw)\n\n')

            #WRITE OUT PORTS
            for port in portList:
                fd.write('class %sSOAPHLS(%sSOAP):\n' % \
                    (port.getBinding().getName(), port.getBinding().getName()))
                fd.write('    def __init__(self, addr, **kw):\n')
                fd.write('        %sSOAP.__init__(self, addr, **kw)\n' % \
                         port.getBinding().getName())
                fd.write('        self._opDict = self._generateOpDict()\n\n')
                fd.write('    def _generateOpDict(self):\n')
                fd.write('        _opDict = {}\n')
                
                for op in port.getBinding().getPortType().getOperationList():
                    inputMsgName = ''
                    outputMsgName = ''
                    if op.getInput():
                        inputMsgName = '%sWrapper' % op.getInput().getMessage().getName()
                    if op.getOutput() and op.getOutput().getMessage():
                        outputMsgName = '%sWrapper' % op.getOutput().getMessage().getName()
                    fd.write("        _opDict['%s'] = (%s, %s)\n" % \
                        (op.getName(), inputMsgName, outputMsgName))
                fd.write("        return _opDict\n\n")

                fd.write('    def getOperations(self):\n')
                fd.write('        return self._opDict\n\n')
                fd.write('    def inputWrapper(self, opName):\n')
                fd.write('        return self._opDict[opName][0]()\n\n')
                fd.write('    def outputWrapper(self, opName):\n')
                fd.write('        return self._opDict[opName][1]()\n\n')
