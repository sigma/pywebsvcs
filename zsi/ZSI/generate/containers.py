############################################################################
# Monte M. Goode, LBNL
# See LBNLCopyright for copyright notice!
###########################################################################

# contains text container classes for new generation generator

# $Id$
import types
from utility import StringWriter, TextProtect, TextProtectAttributeName, GetPartsSubNames
from utility import NamespaceAliasDict as NAD, NCName_to_ClassName as NC_to_CN

import ZSI
from ZSI.TC import _is_xsd_or_soap_ns
from ZSI.wstools import XMLSchema, WSDLTools
from ZSI.wstools.Namespaces import SCHEMA, SOAP, WSDL
from ZSI.wstools.Utility import Base
from ZSI.typeinterpreter import BaseTypeInterpreter
from ZSI.generate import WSISpec, WSInteropError, Wsdl2PythonError, WsdlGeneratorError

ID1 = '    '
ID2 = 2*ID1
ID3 = 3*ID1
ID4 = 4*ID1
ID5 = 5*ID1
ID6 = 6*ID1

KW = {'ID1':ID1, 'ID2':ID2, 'ID3':ID3,'ID4':ID4, 'ID5':ID5, 'ID6':ID6,}

DEC = '_Dec'
DEF = '_Def'

"""
type_class_name -- function to return the name formatted as a type class.
element_class_name -- function to return the name formatted as an element class.
"""
type_class_name = lambda n: '%s%s' %(NC_to_CN(n), DEF)
element_class_name = lambda n: '%s%s' %(NC_to_CN(n), DEC)

def SetTypeNameFunc(func):
    global type_class_name
    type_class_name = func

def SetElementNameFunc(func):
    global element_class_name
    element_class_name = func

def GetClassNameFromSchemaItem(item,do_extended=False):
    '''
    '''
    assert isinstance(item, XMLSchema.XMLSchemaComponent), 'must be a schema item.'
    alias = NAD.getAlias(item.getTargetNamespace())
    if item.isDefinition() is True:
        return '%s.%s' %(alias, NC_to_CN('%s' %type_class_name(item.getAttributeName())))
    return None

def FromMessageGetSimpleElementDeclaration(message):
    '''If message consists of one part with an element attribute,
    and this element is a simpleType return a string representing 
    the python type, else return None.

    '''
    assert isinstance(message, WSDLTools.Message), 'expecting WSDLTools.Message'

    if len(message.parts) == 1 and message.parts[0].element is not None:
       part = message.parts[0]
       nsuri,name = part.element
       wsdl = message.getWSDL()
       types = wsdl.types
       if types.has_key(nsuri) and types[nsuri].elements.has_key(name):
            e = types[nsuri].elements[name]
            if isinstance(e, XMLSchema.ElementDeclaration) is True and e.getAttribute('type'):
                typ = e.getAttribute('type')
                bt = BaseTypeInterpreter()
                ptype = bt.get_pythontype(typ[1], typ[0])
                return ptype

    return None


class AttributeMixIn:
    '''for containers that can declare attributes.
    '''
    typecode = 'attribute_typecode_dict'
    
    def _setAttributes(self, attributes):
        '''parameters
        attributes -- a flattened list of all attributes, 
        from this list all items in attribute_typecode_dict will
        be generated into attrComponents.
        
        returns a list of strings representing the attribute_typecode_dict.
        '''
        atd = AttributeMixIn.typecode
        atd_list = formatted_attribute_list = []
        if not attributes:
            return formatted_attribute_list
        
        atd_list.append('# attribute handling code')
#        atd_list.append('self.%s = {}' %atd)
#        atd_list.append('self.%s.update(%s.%s.%s)' \
#            %(atd, self.getNSAlias(), self.getClassName(), atd))

        for a in attributes:
            
            if a.isWildCard() and a.isDeclaration():
                atd_list.append(\
                    'self.%s[("%s","anyAttribute")] = ZSI.TC.AnyElement()'\
                    % (atd, SCHEMA.XSD3)
                    )
            elif a.isDeclaration():
                tdef = a.getTypeDefinition('type')
                if tdef is not None:
                    tc = '%s.%s(None)' %(NAD.getAlias(tdef.getTargetNamespace()),
                        self.mangle(type_class_name(tdef.getAttributeName()))
                        )
                else:
                    # built-in
                    t = a.getAttribute('type')
                    try:
                        tc = BTI.get_typeclass(t[1], t[0])
                    except:
#                        raise ContainerError,\
#                            'type attribute(%s) not primitive type?: %s' \
#                            %(t, a.getItemTrace())
                        # hand back a string by default.
                        tc = ZSI.TC.String
                            
                    if tc is not None: 
                        tc = '%s()' %tc
                            
                key = None
                if a.getAttribute('form') == 'qualified':
                    key = '("%s","%s")' % ( a.getTargetNamespace(),
                                            a.getAttribute('name') )
                elif a.getAttribute('form') == 'unqualified':
                    key = '"%s"' % a.getAttribute('name')
                else:
                    raise ContainerError, \
                          'attribute form must be un/qualified %s' \
                          % a.getAttribute('form')
                          
                atd_list.append(\
                    'self.%s[%s] = %s' % (atd, key, tc)
                    )
            elif a.isReference() and a.isAttributeGroup():
                # flatten 'em out....
                for ga in a.getAttributeGroup().getAttributeContent():
                    if not ga.isAttributeGroup():
                        attributes += (ga,)
                continue
            elif a.isReference():
                ga = a.getAttributeDeclaration()
                tp = ga.getTypeDefinition('type')
                key = '("%s","%s")' %(ga.getTargetNamespace(),
                         ga.getAttribute('name'))
                         
                if tp is None:
                    # built in simple type
                    try:
                        namespace,typeName = ga.getAttribute('type')
                    except TypeError, ex:
                        # TODO: attribute declaration could be anonymous type
                        # hack in something to work
                        atd_list.append(\
                            'self.%s[%s] = ZSI.TC.String()' %(atd, key)
                            )
#                        raise ContainerError,\
#                              'no type in attribute declaration: %s'\
#                              %a.getItemTrace()
                    else:
                        atd_list.append(\
                            'self.%s[%s] = %s()' %(atd, key, 
                                 BTI.get_typeclass(typeName, namespace))
                            )
                else:
                    typeName = tp.getAttribute('name')
                    namespace = tp.getTargetNamespace()
                    alias = NAD.getAlias(namespace)
                    key = '("%s","%s")' \
                          % (ga.getTargetNamespace(),ga.getAttribute('name'))
                    atd_list.append(\
                        'self.%s[%s] = %s.%s(None)' \
                        % (atd, key, alias, type_class_name(typeName))
                        )
            else:
                raise TypeError, 'expecting an attribute: %s' %a.getItemTrace()
            
        return formatted_attribute_list


class ContainerError(Exception):
    pass


class ContainerBase(Base):
    '''Base class for all Containers.
        func_aname -- function that takes name, and returns aname.
    '''
    func_aname = TextProtectAttributeName
    func_aname = staticmethod(func_aname)

    def __init__(self):
        Base.__init__(self)
        self.content = StringWriter('\n')
        self.__setup   = False
        self.ns    = None

    def __str__(self):
        return self.getvalue()

    # - string content methods
    def mangle(self, s):
        '''class/variable name illegalities
        '''
        return TextProtect(s)

    def write(self, s):
        self.content.write(s)

    def writeArray(self, a):
        self.content.write('\n'.join(a))

    def _setContent(self):
        '''override in subclasses.  formats the content in the desired way.
        '''
        raise NotImplementedError, 'abstract method not implemented'

    def getvalue(self):
        if not self.__setup:
            self._setContent()
            self.__setup = True
            
        return self.content.getvalue()

    # - namespace utility methods
    def getNSAlias(self):
        if self.ns:
            return NAD.getAlias(self.ns)
        raise ContainerError, 'no self.ns attr defined in %s' % self.__class__

    def getNSModuleName(self):
        if self.ns:
            return NAD.getModuleName(self.ns)
        raise ContainerError, 'no self.ns attr defined in %s' % self.__class__

    def getAttributeName(self, name):
        '''represents the aname
        '''
        if self.func_aname is None:
            return name
        assert callable(self.func_aname), \
            'expecting callable method for attribute func_aname, not %s' %type(self.func_aname)
        f = self.func_aname
        return f(name)


# -- containers for services file components

class ServiceContainerBase(ContainerBase):
    clientClassSuffix = "SOAP"
    def __init__(self):
        ContainerBase.__init__(self)
    
    
class ServiceHeaderContainer(ServiceContainerBase):
    imports = ['\nimport urlparse, types',
              'from ZSI.TCcompound import ComplexType, Struct',
              'from ZSI import client',
              'import ZSI'
              ]
               
    def __init__(self, do_extended=False):
        ServiceContainerBase.__init__(self)
        
        self.basic = self.imports[:]
        self.types = None
        self.messages = None
        self.extras = []
        self.do_extended = do_extended

    def setTypesModuleName(self, module):
        self.types = module

    def setMessagesModuleName(self, module):
        self.messages = module

    def appendImport(self, statement):
        '''append additional import statement(s).
        import_stament -- tuple or list or str 
        '''
        if type(statement) in (list,tuple):
            self.extras += statement
        else:
            self.extras.append(statement)

    def _setContent(self):
        if self.messages:
            self.write('from %s import *' % self.messages)
        if self.types:
            self.write('from %s import *' % self.types)

        imports = self.basic[:]
        imports += self.extras
        self.writeArray(imports)


class ServiceLocatorContainer(ServiceContainerBase):
    def __init__(self):
        ServiceContainerBase.__init__(self)
        self.serviceName = None
        self.portInfo = []
        self.locatorName = None
        self.portMethods = []

    def setUp(self, service):
        assert isinstance(service, WSDLTools.Service), \
           'expecting WDSLTools.Service instance.'

        self.serviceName = service.name
        for p in service.ports:
            try:
                ab = p.getAddressBinding()
            except WSDLTools.WSDLError, ex:
                self.logger.warning('Skip port(%s), missing address binding' %p.name)
                continue
            if isinstance(ab, WSDLTools.SoapAddressBinding) is False:
                self.logger.warning('Skip port(%s), not a SOAP-1.1 address binding' %p.name)
                continue

            info = (p.getBinding().getPortType().name, p.getBinding().name, ab.location)
            self.portInfo.append(info) 

    def getLocatorName(self):
        '''return class name of generated locator.
        '''
        return self.locatorName

    def getPortMethods(self):
        '''list of get port accessor methods of generated locator class.
        '''
        return self.portMethods

    def _setContent(self):
        if not self.serviceName:
            raise ContainerError, 'no service name defined!'

        self.serviceName = self.mangle(self.serviceName)
        self.locatorName = '%sLocator' %self.serviceName
        locator = ['# Locator', 'class %s:' %self.locatorName, ]
        self.portMethods = []
        for p in self.portInfo:
            ptName = p[0]
            bName  = p[1]
            sAdd   = p[2]
            method = 'get%s' %ptName
            pI = [
                '%s%s_address = "%s"' % (ID1, ptName, sAdd),
                '%sdef get%sAddress(self):' % (ID1, ptName),
                '%sreturn %sLocator.%s_address' % (ID2,
                                                   self.serviceName,ptName),
                '%sdef %s(self, url=None, **kw):' %(ID1, method),
                '%sreturn %s%s(url or %sLocator.%s_address, **kw)' \
                % (ID2, bName, self.clientClassSuffix, self.serviceName, ptName),
                ]
            self.portMethods.append(method)
            locator += pI

        self.writeArray(locator)


class ServiceOperationsClassContainer(ServiceContainerBase):
    '''
    class variables:
        readerclass --  
        writerclass --
    '''
    readerclass = None
    writerclass = None
    
    def __init__(self, useWSA=False, do_extended=False, wsdl=None):
        '''Parameters:
        name -- binding name
        property -- resource properties
        useWSA   -- boolean, enable ws-addressing
        name -- binding name
        '''
        ServiceContainerBase.__init__(self)
        self.useWSA = useWSA
        self.rProp = None
        self.bName = None
        self.readerclass = self.writerclass = None
        self.operations = []
        self.do_extended = do_extended
        self._wsdl = wsdl # None unless do_extended == True

    def setReaderClass(cls, className):
        '''specify a reader class name, this must be imported
        in service module.
        '''
        cls.readerclass = className
    setReaderClass = classmethod(setReaderClass)

    def setWriterClass(cls, className):
        '''specify a writer class name, this must be imported
        in service module.
        '''
        cls.writerclass = className 
    setWriterClass = classmethod(setWriterClass)

    def getOperationContainers(self):
        '''retrieve list of ServiceOperationContainer instances.
        '''
        assert self.bName is not None, 'call setUp first.'
        return self.operations

    def addOperation(self, name, port):
        '''
        name -- Operation Name.
        port -- WSDL.Port instance
        '''
        bop = port.getBinding().operations.get(name)
        op = port.getBinding().getPortType().operations.get(name)
        if op is None or bop is None:
            raise Wsdl2PythonError, 'no matching portType/Binding operation(%s)' % bop.name

        c = ServiceOperationContainer(name, useWSA=self.useWSA, do_extended=self.do_extended, wsdl=self._wsdl)
        c.setUp(port)
        self.operations.append(c)

    def setUp(self, port):
        '''This method finds all SOAP Binding Operations, it will skip 
        all bindings that are not SOAP.  
        port -- WSDL.Port instance
        '''
        assert isinstance(port, WSDLTools.Port), 'expecting WSDLTools Port instance'

        self.bName = port.getBinding().name
        self.rProp = port.getBinding().getPortType().getResourceProperties() 

        soap_binding = port.getBinding().findBinding(WSDLTools.SoapBinding)
        if soap_binding is None:
            raise Wsdl2PythonError, 'port(%s) missing WSDLTools.SoapBinding' %port.name

        for bop in port.getBinding().operations:
            soap_bop = bop.findBinding(WSDLTools.SoapOperationBinding)
            if soap_bop is None:
                self.logger.warning(\
                    'Skip port(%s) operation(%s) no SOAP Binding Operation' %(port.name, bop.name),
                )
                continue

            #soapAction = soap_bop.soapAction
            if bop.input is not None:
                soapBodyBind = bop.input.findBinding(WSDLTools.SoapBodyBinding)
                if soapBodyBind is None:
                    self.logger.warning(\
                        'Skip port(%s) operation(%s) Bindings(%s) not supported'\
                        %(port.name, bop.name, bop.extensions)
                    )
                    continue
                
            self.addOperation(bop.name, port)

    def _setContent(self):
        if self.useWSA is True:
            ctorArgs = 'endPointReference=None, **kw'
            epr      = 'self.endPointReference = endPointReference'
        else:
            ctorArgs = '**kw'
            epr      = '# no ws-addressing'

        if self.rProp:
            rprop = 'kw.setdefault("ResourceProperties", ("%s","%s"))'\
                %(self.rProp[0], self.rProp[1])
        else:
            rprop = '# no resource properties'

        methods = [
            '# Methods',
            'class %s%s:' % (self.bName, self.clientClassSuffix),
            '%sdef __init__(self, url, %s):' % (ID1, ctorArgs),
            '%skw.setdefault("readerclass", %s)' % (ID2, self.readerclass),
            '%skw.setdefault("writerclass", %s)' % (ID2, self.writerclass),
            '%s%s' % (ID2, rprop),
            '%sself.binding = client.Binding(url=url, **kw)' %ID2,
            '%s%s' % (ID2,epr),
            ]

        for op in self.operations:
            methods += [ op.getvalue() ]

        self.writeArray(methods)


class ServiceOperationContainer(ServiceContainerBase):
    def __init__(self, name, useWSA=False, soapAction=None, do_extended=False, wsdl=None):
        '''Parameters:
        name -- binding name
        useWSA   -- boolean, enable ws-addressing
        soapAction -- soapaction value for this operation
        '''
        ServiceContainerBase.__init__(self)
        self.name = name
        self.useWSA  = useWSA
        self.port = None
        self.soapaction = None
        self.inputName  = None
        self.outputName = None
        self.inputSimpleType  = None
        self.outputSimpleType = None
        self.inputAction  = None
        self.outputAction = None
        self.do_extended = do_extended
        if do_extended:
            self._wsdl = wsdl

    def hasInput(self):
        return self.inputName is not None

    def hasOutput(self):
        return self.outputName is not None

    def isRPC(self):
        binding = self.port.getBinding()
        soap = binding.findBinding(WSDLTools.SoapBinding)
        return soap.style=='rpc'

    def isLiteral(self, input=True):
        binding = self.port.getBinding()
        bop = binding.operations.get(self.name)
        msgrole = bop.input
        if input is False:
            msgrole = bop.output
        body = msgrole.findBinding(WSDLTools.SoapBodyBinding)
        return body.use=='literal'

    def isSimpleType(self, input=True):
        if input is False:
            return self.outputSimpleType
        return self.inputSimpleType

    def getOperation(self):
        return self.port.getBinding().getPortType().operations.get(self.name)

    def getBOperation(self):
        return self.port.getBinding().get(self.name)

    def getOperationName(self):
        return self.name

    def setUp(self, port):
        '''Parameters:
	port -- WSDLTools Port instance.
        '''
        assert isinstance(port, WSDLTools.Port), 'expecting WSDLTools Operation instance'

        self.port = port
        name = self.name
        bop = port.getBinding().operations.get(name)
        op = port.getBinding().getPortType().operations.get(name)
        if op is None or bop is None:
            raise Wsdl2PythonError, 'no matching portType/Binding operation(%s)' %name

        soap_bop = bop.findBinding(WSDLTools.SoapOperationBinding)
        assert soap_bop is not None, 'expecting SOAP Bindings only.'

        # set encodingStyle
        if bop.input is not None:
            sbody = bop.input.findBinding(WSDLTools.SoapBodyBinding)
            self.encodingStyle = None
            if sbody.use == 'encoded':
                assert sbody.encodingStyle == SOAP.ENC,\
                    'Supporting encodingStyle=%s, not %s' %(SOAP.ENC, sbody.encodingStyle)
                self.encodingStyle = sbody.encodingStyle

        self.soapaction=soap_bop.soapAction
        if op.input:
            self.inputName  = op.getInputMessage().name
            self.inputSimpleType = FromMessageGetSimpleElementDeclaration(op.getInputMessage())
            self.inputAction = op.getInputAction()
        if op.output:
            self.outputName = op.getOutputMessage().name
            self.outputSimpleType = FromMessageGetSimpleElementDeclaration(op.getOutputMessage())
            self.outputAction = op.getOutputAction()

    def _setContent(self):
        '''create string representation of operation.
        '''
        kwstring = 'kw = {}'
        tCheck = 'if isinstance(request, %s) is False:' % self.inputName
        bindArgs = ''
        if self.encodingStyle is not None:
            bindArgs = 'encoding="%s", ' %self.encodingStyle

        if self.useWSA:
            wsactionIn = 'wsaction = "%s"' % self.inputAction
            wsactionOut = 'wsaction = "%s"' % self.outputAction
            bindArgs += 'wsaction=wsaction, endPointReference=self.endPointReference, '
            responseArgs = ', wsaction=wsaction'
        else:
            wsactionIn = '# no input wsaction'
            wsactionOut = '# no output wsaction'
            responseArgs = ''

        bindArgs += '**kw)'

        if self.do_extended:
            inputName = self.getOperation().getInputMessage().name
            wrap_str = ""
            partsList = self.getOperation().getInputMessage().parts.values()
            try:
                subNames = GetPartsSubNames(partsList, self._wsdl)
            except TypeError, ex:
                raise Wsdl2PythonError,\
                    "Extended generation failure: only supports doc/lit, "\
                    +"and all element attributes (<message><part element="\
                    +"\"my:GED\"></message>) must refer to single global "\
                    +"element declaration with complexType content.  "\
                    +"\n\n**** TRY WITHOUT EXTENDED ****\n"
                
            args = []
            for pa in subNames:
                args += pa

            for arg in args:
                wrap_str += "%srequest.%s = %s\n" % (ID2,
                                                     self.getAttributeName(arg),
                                                     self.mangle(arg))

            #args = [pa.name for pa in self.getOperation().getInputMessage().parts.values()]
            argsStr = ",".join(args)
            if len(argsStr) > 1: # add inital comma if args exist
                argsStr = ", " + argsStr

            method = [
                '%s# op: %s' % (ID1, self.getOperation().getInputMessage()),
                '%sdef %s(self%s):' % (ID1, self.name, argsStr),
                '\n%srequest = %s()' % (ID2, self.inputName),
                '%s' % (wrap_str),
                '%s%s' % (ID2, kwstring),
                '%s%s' % (ID2, wsactionIn),
                '%sself.binding.Send(None, None, request, soapaction="%s", %s'\
                %(ID2, self.soapaction, bindArgs),
            ]
        else:
            method = [
                '%s# op: %s' % (ID1, self.name),
                '%sdef %s(self, request):' % (ID1, self.name),
                '%s%s' % (ID2, tCheck),
                '%sraise TypeError, "%%s incorrect request type" %% (%s)' %(ID3, 'request.__class__'),
                '%s%s' % (ID2, kwstring),
                '%s%s' % (ID2, wsactionIn),
                '%sself.binding.Send(None, None, request, soapaction="%s", %s'\
                %(ID2, self.soapaction, bindArgs),
            ]

        if self.outputName:
            response = ['%s%s' % (ID2, wsactionOut),]
            response.append('%sresponse = self.binding.Receive(%s.typecode%s)' %(ID2, self.outputName, responseArgs))
            if self.outputSimpleType:
                response.append('%sreturn %s(response)' %(ID2, self.outputName))
            else: 
                rCheck = 'if isinstance(response, %s.typecode.pyclass) is False:' %self.outputName
                response.append('%s%s' %(ID2, rCheck))
                response.append('%sraise TypeError, "%%s incorrect response type" %% (%s)' %(ID3, 'response.__class__'))

                if self.do_extended:
                    partsList = self.getOperation().getOutputMessage().parts.values()
                    subNames = GetPartsSubNames(partsList, self._wsdl)
                    args = []
                    for pa in subNames:
                        args += pa

                    for arg in args:
                        response.append('%s%s = response.%s' % (ID2, self.mangle(arg), self.getAttributeName(arg)) )
                    margs = ",".join(args)
                    response.append("%sreturn %s" % (ID2, margs) )
                else:
                    response.append('%sreturn response' %ID2)
            method += response

        self.writeArray(method)


class MessageContainerInterface:
    
    def setUp(self, port, soc, input):
        '''sets the attribute _simple which represents a 
        primitive type message represents, or None if not primitive.
 
        soc -- WSDLTools.ServiceOperationContainer instance
        port -- WSDLTools.Port instance
        input-- boolean, input messasge or output message of operation.
        '''
        raise NotImplementedError, 'Message container must implemented setUp.'


class ServiceDocumentLiteralMessageContainer(ServiceContainerBase, MessageContainerInterface):

    def __init__(self, do_extended=False):

        ServiceContainerBase.__init__(self)
        self.do_extended=do_extended

    def setUp(self, port, soc, input):
        content = self.content
        # TODO: check soapbody for part name
        simple = self._simple = soc.isSimpleType(soc.getOperationName())
        name = soc.getOperationName()

        # Document/literal
        operation = port.getBinding().getPortType().operations.get(name)
        bop = port.getBinding().operations.get(name)
        soapBodyBind = None
        if input is True:
            soapBodyBind = bop.input.findBinding(WSDLTools.SoapBodyBinding)
            message = operation.getInputMessage()
        else:
            soapBodyBind = bop.output.findBinding(WSDLTools.SoapBodyBinding)
            message = operation.getOutputMessage()
            
        # using underlying data structure to avoid phantom problem.
#        parts = message.parts.data.values()
#        if len(parts) > 1:
#            raise Wsdl2PythonError, 'not suporting multi part doc/lit msgs'
        if len(message.parts) == 0:
            raise Wsdl2PythonError, 'must specify part for doc/lit msg'
        
        p = None
        if soapBodyBind.parts is not None:
            if len(soapBodyBind.parts) > 1:
                raise Wsdl2PythonError,\
                    'not supporting multiple parts in soap body'
            if len(soapBodyBind.parts) == 0:
                return
            
            p = message.parts.get(soapBodyBind.parts[0])
        
        # XXX: Allow for some slop
        p = p or message.parts[0]
    
        if p.type:
            raise  Wsdl2PythonError, 'no doc/lit suport for <part type>'
        
        if not p.element:
            return
        
        content.ns = p.element[0]
        content.pName = p.element[1]
        content.mName = message.name
        
    def _setContent(self):
        '''create string representation of doc/lit message container.  If 
        message element is simple(primitive), use python type as base class.
        '''
        try:
            simple = self._simple
        except AttributeError:
            raise RuntimeError, 'call setUp first'
        
        # TODO: Hidden contract.  Must set self.ns before getNSAlias...
        #  File "/usr/local/python/lib/python2.4/site-packages/ZSI/generate/containers.py", line 625, in _setContent
        #    kw['message'],kw['prefix'],kw['typecode'] = \
        #  File "/usr/local/python/lib/python2.4/site-packages/ZSI/generate/containers.py", line 128, in getNSAlias
        #    raise ContainerError, 'no self.ns attr defined in %s' % self.__class__
        # ZSI.generate.containers.ContainerError: no self.ns attr defined in ZSI.generate.containers.ServiceDocumentLiteralMessageContainer
        #            
        self.ns = self.content.ns
        
        
        kw = KW.copy()
        kw['message'],kw['prefix'],kw['typecode'] = \
            self.content.mName, self.getNSAlias(), element_class_name(self.content.pName)
        
        # These messsages are just global element declarations
        self.writeArray(['%(message)s = %(prefix)s.%(typecode)s().pyclass' %kw])


class ServiceRPCEncodedMessageContainer(ServiceContainerBase, MessageContainerInterface):
    def setUp(self, port, soc, input):
        '''
        Instance Data: 
           op    -- WSDLTools Operation instance
           bop   -- WSDLTools BindingOperation instance
           input -- boolean input/output
        '''
        name = soc.getOperationName()
        bop = port.getBinding().operations.get(name)
        op = port.getBinding().getPortType().operations.get(name)

        assert op is not None, 'port has no operation %s' %name
        assert bop is not None, 'port has no binding operation %s' %name

        self.input = input
        self.op = op
        self.bop = bop

    def _setContent(self):
        try: 
            self.op
        except AttributeError:
            raise RuntimeError, 'call setUp first'

        pname = self.op.name
        msgRole = self.op.input
        msgRoleB = self.bop.input
        if self.input is False:
            pname = '%sResponse' %self.op.name
            msgRole = self.op.output
            msgRoleB = self.bop.output

        sbody = msgRoleB.findBinding(WSDLTools.SoapBodyBinding)
        if not sbody or not sbody.namespace:
            raise WSInteropError, WSISpec.R2717

        assert sbody.use == 'encoded', 'Expecting use=="encoded"'
        encodingStyle = sbody.encodingStyle

        assert encodingStyle == SOAP.ENC,\
            'Supporting encodingStyle=%s, not %s' %(SOAP.ENC, encodingStyle)

        namespace = sbody.namespace
        tcb = MessageTypecodeContainer(\
                  tuple(msgRole.getMessage().parts.list),
              )
        ofwhat = '[%s]' %tcb.getTypecodeList()
        pyclass = msgRole.getMessage().name
        message = [
            'class %s:' %pyclass,
            '%sdef __init__(self):' % ID1,
            ]

        for aname in tcb.getAttributeNames():
            message.append('%sself.%s = None' %(ID2, aname))
        message.append('%sreturn' %ID2)

        message.append('%s.typecode = Struct(pname=("%s","%s"), ofwhat=%s, pyclass=%s, encoded="%s")' \
            %(pyclass, sbody.namespace, pname, ofwhat, pyclass, namespace),)
        self.writeArray(message)


class ServiceRPCLiteralMessageContainer(ServiceContainerBase, MessageContainerInterface):
    def setUp(self, port, soc, input):
        '''
        Instance Data: 
           op    -- WSDLTools Operation instance
           bop   -- WSDLTools BindingOperation instance
           input -- boolean input/output
        '''
        name = soc.getOperationName()
        bop = port.getBinding().operations.get(name)
        op = port.getBinding().getPortType().operations.get(name)

        assert op is not None, 'port has no operation %s' %name
        assert bop is not None, 'port has no binding operation %s' %name

        self.op = op
        self.bop = bop
        self.input = input

    def _setContent(self):
        try:
            self.op
        except AttributeError:
            raise RuntimeError, 'call setUp first' 

        operation = self.op
        input = self.input
        pname = operation.name
        msgRole = operation.input
        msgRoleB = self.bop.input
        if input is False:
            pname = '%sResponse' %operation.name
            msgRole = operation.output
            msgRoleB = self.bop.output

        sbody = msgRoleB.findBinding(WSDLTools.SoapBodyBinding)
        if not sbody or not sbody.namespace:            
            raise WSInteropError, WSISpec.R2717

        mName = msgRole.getMessage().name
        parts = msgRole.getMessage().parts.list
        tcb = MessageTypecodeContainer(tuple(parts))
        ofwhat = '[%s]' %tcb.getTypecodeList()
        pyclass = mName

        message = [
            'class %s:' %mName,
            '%sdef __init__(self):' % ID1,
            ]

        anames = tcb.getAttributeNames()
        for aname in anames:
            message.append('%sself.%s = None' %(ID2, aname))
        if not len(anames):
            message.append('%sreturn' %ID2)

        message.append('%s.typecode = Struct(pname=("%s","%s"), ofwhat=%s, pyclass=%s)' \
            %(mName, sbody.namespace, pname, ofwhat, pyclass),)
        self.writeArray(message)



TypesContainerBase = ContainerBase
#class TypesContainerBase(ContainerBase):
#    '''base class for containers of type file components
#    '''
#    def __init__(self):
#        ContainerBase.__init__(self)


class TypesHeaderContainer(TypesContainerBase):
    '''imports for all generated types modules.
    '''
    imports = [
        'import ZSI',
        'import ZSI.TCcompound',
        'from ZSI.TC import ElementDeclaration,TypeDefinition',
    ]

    def _setContent(self):
        self.writeArray(TypesHeaderContainer.imports)


NamespaceClassContainerBase = TypesContainerBase
#class NamespaceClassContainerBase(TypesContainerBase):
#    def __init__(self):
#        TypesContainerBase.__init__(self)
        

class NamespaceClassHeaderContainer(NamespaceClassContainerBase):

    def _setContent(self):

        head = [
            '#' * 30,
            '# targetNamespace',
            '# %s' % self.ns,
            '#' * 30 + '\n',
            'class %s:' % self.getNSAlias(),
            '%stargetNamespace = "%s"' % (ID1, self.ns)
            ]

        self.writeArray(head)

class NamespaceClassFooterContainer(NamespaceClassContainerBase):

    def _setContent(self):

        foot = [
            '# end class %s (tns: %s)' % (self.getNSAlias(), self.ns),
            ]

        self.writeArray(foot)


BTI = BaseTypeInterpreter()
class TypecodeContainerBase(TypesContainerBase):
    '''Base class for all classes representing anything
    with element content.

    class variables:
        mixed_content_aname -- text content will be placed in this attribute.
        attributes_aname -- attributes will be placed in this attribute.
        metaclass -- set this attribute to specify a pyclass __metaclass__
    '''
    mixed_content_aname = 'text'
    attributes_aname = 'attrs'
    metaclass = None

    def __init__(self, do_extended=False, extPyClasses=None):
        TypesContainerBase.__init__(self)
        self.name = None

        # attrs for model groups and others with elements, tclists, etc...
        self.allOptional = False
        self.mgContent = None
        self.contentFlattened = False
        self.elementAttrs = []
        self.elementsSet = False
        self.tcListElements = []
        self.tcListSet = False

        self.localTypes = []

        # used when processing nested anonymous types
        self.parentClass = None

        # used when processing attribute content

        self.mixed = False
        self.extraFlags = ''

        self.attrComponents = None

        # Used if an external pyclass was specified for this type.
        self.do_extended = do_extended
        if extPyClasses == None:
            self.extPyClasses = {}
        else:
            self.extPyClasses = extPyClasses

    def getvalue(self):
        out = ContainerBase.getvalue(self)
        for item in self.localTypes:
            content = None
            assert True is item.isElement() is item.isLocal(), 'expecting local elements only'

            etp = item.content
            qName = item.getAttribute('type')
            if not qName:
                etp = item.content
                local = True
            else:
                etp = item.getTypeDefinition('type')

            if etp is None:
                if local is True:
                    content = ElementLocalComplexTypeContainer(do_extended=self.do_extended)
                else:
                    content = ElementSimpleTypeContainer()
            elif etp.isLocal() is False:
                content = ElementGlobalDefContainer()
            elif etp.isSimple() is True:
                content = ElementLocalSimpleTypeContainer()
            elif etp.isComplex():
                content = ElementLocalComplexTypeContainer(do_extended=self.do_extended)
            else:
                raise Wsdl2PythonError, "Unknown element declaration: %s" %item.getItemTrace()

            content.setUp(item)

            out += '\n\n'
            if self.parentClass:
                content.parentClass = \
                    '%s.%s' %(self.parentClass, self.getClassName())
            else:
                content.parentClass = '%s.%s' %(self.getNSAlias(), self.getClassName())

            for l in content.getvalue().split('\n'):
                if l: out += '%s%s\n' % (ID1, l)
                else: out += '\n'

            out += '\n\n'

        return out

    def getAttributeName(self, name):
        '''represents the aname
        '''
        if self.func_aname is None:
            return name
        assert callable(self.func_aname), \
            'expecting callable method for attribute func_aname, not %s' %type(self.func_aname)
        f = self.func_aname
        return f(name)

    def getMixedTextAName(self):
        '''returns an aname representing mixed text content.
        '''
        return self.getAttributeName(self.mixed_content_aname)

    def getClassName(self):

        if not self.name:
            raise ContainerError, 'self.name not defined!'
        if not hasattr(self.__class__, 'type'):
            raise ContainerError, 'container type not defined!'

        #suffix = self.__class__.type
        if self.__class__.type == DEF:
            classname = type_class_name(self.name)
        elif self.__class__.type == DEC:
            classname = element_class_name(self.name)

        return self.mangle( classname )

    def hasExtPyClass(self):
        if self.name in self.extPyClasses:
            return True
        else:
            return False

    def getPyClass(self):
        '''Name of generated inner class that will be specified as pyclass.
        '''
        if self.hasExtPyClass():
            classInfo = self.extPyClasses[self.name]
            return ".".join(classInfo)
        else:
            return 'Holder'
    
    def getPyClassDefinition(self):
        '''Return a list containing pyclass definition.
        '''
        kw = KW.copy()
        if self.hasExtPyClass():
            classInfo = self.extPyClasses[self.name]
            kw['classInfo'] = classInfo[0]
            return ["%(ID3)simport %(classInfo)s" %kw ]
        
        kw['pyclass'] = self.getPyClass()
        
        definition = []
        definition.append('%(ID3)sclass %(pyclass)s:' %kw)
        if self.metaclass is not None:
            kw['type'] = self.metaclass
            definition.append('%(ID4)s__metaclass__ = %(type)s' %kw)
        definition.append('%(ID4)stypecode = self' %kw)
        definition.append('%(ID4)sdef __init__(self):' %kw)
        definition.append('%(ID5)s# pyclass' %kw)

        # JRB HACK need to call _setElements via getElements
        self.getElements()
        # JRB HACK need to indent additional one level
        for el in self.elementAttrs:
            kw['element'] = el
            definition.append('%(ID2)s%(element)s' %kw)
        definition.append('%(ID5)sreturn' %kw)

        # JRB give pyclass a descriptive name
        if self.name is not None:
            kw['name'] = self.name
            definition.append(\
                '%(ID3)s%(pyclass)s.__name__ = "%(name)s_Holder"' %kw
                )

        return definition

    def nsuriLogic(self):
        '''set a variable "ns" that represents the targetNamespace in
        which this item is defined.  Used for namespacing local elements.
        '''
        if self.parentClass:
            return 'ns = %s.%s.schema' %(self.parentClass, self.getClassName())
        return 'ns = %s.%s.schema' %(self.getNSAlias(), self.getClassName())

    def schemaTag(self):
        if self.ns is not None:
            return 'schema = "%s"' % self.ns
        raise ContainerError, 'failed to set schema targetNamespace(%s)' %(self.__class__)
    
    def typeTag(self):
        if self.name is not None:
            return 'type = (schema, "%s")' % self.name
        raise ContainerError, 'failed to set type name(%s)' %(self.__class__)
    
    def literalTag(self):
        if self.name is not None:
            return 'literal = "%s"' % self.name
        raise ContainerError, 'failed to set element name(%s)' %(self.__class__)

    def getExtraFlags(self):
        if self.mixed:
            self.extraFlags += 'mixed=True, mixed_aname="%s", ' %self.getMixedTextAName()

        return self.extraFlags

    def simpleConstructor(self, superclass=None):

        if superclass:
            return '%s.__init__(self, **kw)' % superclass
        else:
            return 'def __init__(self, **kw):'

    def pnameConstructor(self, superclass=None):

        if superclass:
            return '%s.__init__(self, pname, **kw)' % superclass
        else:
            return 'def __init__(self, pname, **kw):'

    # _flattenContent() is a pre-processor called before either the
    # elements or typecode strings are generated.  it flattens out
    # embedded/anonymous model group elements.  _setElements() and
    # _setTypecodeList() skip the model groups and pay attention
    # to the elements contained therein.

    def _flattenContent(self):
        if not self.contentFlattened:
            self.contentFlattened = True
            if type(self.mgContent) is not tuple:
                raise TypeError, 'expecting tuple for mgContent, not: %s' %type(self.mgContent)
            for c in self.mgContent:
                if c.isChoice() or c.isSequence():
                    self.mgContent += c.content

    # getElements() and _setElements() generate the class variable
    # elements lists in definition classes

    def _setElements(self):
        if type(self.mgContent) is not tuple:
            raise TypeError, 'expecting tuple for mgContent got %s' %type(self.mgContent)

        for c in self.mgContent:
            if c.isDeclaration() and c.isElement():
                if c.getAttribute('maxOccurs') == 'unbounded':
                    defaultValue = "[]"
                else:
                    defaultValue = "None"
                if c.getAttribute('name'):
                    e = '%sself.%s = %s' \
                        %(ID3, self.getAttributeName(c.getAttribute('name')), defaultValue)
                    self.elementAttrs.append(e)
                elif c.isWildCard():
                    e = '%sself.%s = %s' % (ID3, self.getAttributeName(c.getAttribute('name')), defaultValue)
                else:
                    raise ContainerError, 'This is not an element declaration: %s' %c.getItemTrace()
            elif c.isReference():
                if c.getAttribute('ref')[1]:
                    e = '%sself._%s = None' \
                        % (ID3,self.mangle(c.getAttribute('ref')[1]))
                    self.elementAttrs.append(e)
                else:
                    raise ContainerError, 'ouch as well'
            elif c.isSequence() or c.isChoice():
                if not self.contentFlattened:
                    raise ContainerError, 'unflattened content found!'
                else:
                    # model group contents already flattened
                    pass
            else:
                raise ContainerError, 'unexpected item: %s' % c.getItemTrace()

    def getElements(self):
        if not self.elementsSet:
            self._flattenContent()
            self._setElements()
            self.elementsSet = True

        return '\n'.join(self.elementAttrs)

    def _setTypecodeList(self):
        '''getTypecodeList and _setTypecodeList generates the TClist 
        strings where appropriate.

            mgContent -- 
            localTypes -- produce local class definitions later
            tcListElements -- elements, local/global 
 
        '''
        if type(self.mgContent) is not tuple:
            raise TypeError, 'expecting tuple for mgContent got %s' %type(self.mgContent)

        for c in self.mgContent:
            tc = TcListComponentContainer()
            min,max,nil = self._getOccurs(c)
            tc.setOccurs(min, max, nil)
            processContents = self._getProcessContents(c)
            tc.setProcessContents(processContents)

            if c.isDeclaration() and c.isElement():
                global_type = c.getAttribute('type')
                content = getattr(c, 'content', None)
                if c.isLocal() and c.isQualified() is False:
                    tc.unQualified()

                if c.isWildCard():
                    tc.setStyleAnyElement()
                elif global_type is not None:
                    tc.name = c.getAttribute('name')
                    ns = global_type[0]
                    if ns in SCHEMA.XSD_LIST:
                        tpc = BTI.get_typeclass(global_type[1],global_type[0])
                        tc.klass = tpc
                    elif (self.ns,self.name) == global_type:
                        # elif self._isRecursiveElement(c)
                        # TODO: Remove this, it only works for 1 level.
                        tc.setStyleRecursion()
                    else:
                        tc.klass = '%s.%s' % (NAD.getAlias(ns),
                            type_class_name(global_type[1]))
                    del ns
                elif content is not None and content.isLocal() and content.isComplex():
                    tc.name = c.getAttribute('name')
                    tc.klass = 'self.__class__.%s' % (element_class_name(tc.name) )
                    tc.setStyleElementReference()
                    self.localTypes.append(c)
                elif content is not None and content.isLocal() and content.isSimple():
                    # Local Simple Type
                    tc.name = c.getAttribute('name')
                    tc.klass = 'self.__class__.%s%s' % (element_class_name(tc.name))
                    tc.setStyleElementReference()
                    self.localTypes.append(c)
                else:
                    raise ContainerError, 'unexpected item: %s' % c.getItemTrace()

            elif c.isReference():
                # element references
                ns = c.getAttribute('ref')[0]
                tc.klass = '%s.%s' % (NAD.getAlias(ns),
                                          element_class_name(c.getAttribute('ref')[1]) )
                tc.setStyleElementReference()
            elif c.isSequence() or c.isChoice():
                if not self.contentFlattened:
                    raise ContainerError, 'unflattened content found!'
                continue
            else:
                raise ContainerError, 'unexpected item: %s' % c.getItemTrace()

            self.tcListElements.append(tc)

    def getTypecodeList(self):
        if not self.tcListSet:
            self._flattenContent()
            self._setTypecodeList()
            self.tcListSet = True

        list = []
        for e in self.tcListElements:
            list.append(str(e))

        return ', '.join(list)

    # the following _methods() are utility methods used during
    # TCList generation, et al.
    
    def _getOccurs(self, e):
        
        nillable = e.getAttribute('nillable')
        if nillable == 'true':
            nillable = True
        else:
            nillable = False
            
        maxOccurs = e.getAttribute('maxOccurs')
        if maxOccurs == 'unbounded':
            maxOccurs = '"%s"' %maxOccurs
            
        minOccurs = e.getAttribute('minOccurs')
        
        if self.allOptional is True:
            #JRB Hack
            minOccurs = '0'
            maxOccurs = '"unbounded"'

        return minOccurs,maxOccurs,nillable

    def _getProcessContents(self, e):
        processContents = e.getAttribute('processContents')
        return processContents

    def getBasesLogic(self, indent):
        try:
            prefix = NAD.getAlias(self.sKlassNS)
        except WsdlGeneratorError, ex:
            # XSD or SOAP
            raise

        bases = []
        bases.append(\
            'if %s.%s not in %s.%s.__bases__:'\
            %(NAD.getAlias(self.sKlassNS), type_class_name(self.sKlass), self.getNSAlias(), self.getClassName()),
        )
        bases.append(\
            '%sbases = list(%s.%s.__bases__)'\
            %(ID1,self.getNSAlias(),self.getClassName()),
        )
        bases.append(\
            '%sbases.insert(0, %s.%s)'\
            %(ID1,NAD.getAlias(self.sKlassNS), type_class_name(self.sKlass) ),
        )
        bases.append(\
            '%s%s.%s.__bases__ = tuple(bases)'\
            %(ID1, self.getNSAlias(), self.getClassName())
        )

        s = ''
        for b in bases:
            s += '%s%s\n' % (indent, b)

        return s


class MessageTypecodeContainer(TypecodeContainerBase):
    '''Used for RPC style messages, where we have 
    serveral parts serialized within a rpc wrapper name.
    '''
    def __init__(self, parts=None):
        TypecodeContainerBase.__init__(self)
        self.mgContent = parts

    def _getOccurs(self, e):
        '''return a 3 item tuple 
        '''
        minOccurs = maxOccurs = '1'
        nillable = True
        return minOccurs,maxOccurs,nillable

    def _setTypecodeList(self):
        assert type(self.mgContent) is tuple,\
            'expecting tuple for mgContent not: %s' %type(self.mgContent)

        for p in self.mgContent:
            # JRB
            #   not sure what needs to be set for tc, this should be
            #   the job of the constructor or a setUp method.
            min,max,nil = self._getOccurs(p)
            if p.element:
                raise  WSInteropError, WSISpec.R2203
            elif p.type: 
                nsuri,name = p.type
                tc = RPCMessageTcListComponentContainer(qualified=False)
                tc.setOccurs(min, max, nil)
                tc.name = p.name
                if nsuri in SCHEMA.XSD_LIST:
                    tpc = BTI.get_typeclass(name, nsuri)
                    tc.klass = tpc
                else:
                    tc.klass = '%s.%s' % (NAD.getAlias(nsuri), type_class_name(name) )
            else:
                raise ContainerError, 'part must define an element or type attribute'

            self.tcListElements.append(tc)

    def getTypecodeList(self):
        if not self.tcListSet:
            self._setTypecodeList()
            self.tcListSet = True

        list = []
        for e in self.tcListElements:
            list.append(str(e))
        return ', '.join(list)

    def getAttributeNames(self):
        '''returns a list of anames representing the parts
        of the message.
        '''
        return map(lambda e: self.getAttributeName(e.name), self.tcListElements)

    def setParts(self, parts):
        self.mgContent = parts

#class TcListComponentContainer(TypecodeContainerBase):
class TcListComponentContainer(ContainerBase):
    '''Encapsulates a single value in the TClist list.
    it inherits TypecodeContainerBase only to get the mangle() method,
    it does not call the baseclass ctor.
    
    TODO: Change this inheritance scheme.
    '''
    
    def __init__(self, qualified=True):
        '''
        qualified -- qualify element.  All GEDs should be qualified,
            but local element declarations qualified if form attribute
            is qualified, else they are unqualified. Only relevant for
            standard style.
        '''
        #TypecodeContainerBase.__init__(self)
        ContainerBase.__init__(self)

        self.qualified = qualified
        self.name = None
        self.klass = None
        
        self.min = None
        self.max = None
        self.nil = None
        self.style = None
        self.setStyleElementDeclaration()

    def setOccurs(self, min, max, nil):
        self.min = min
        self.max = max
        self.nil = nil

    def setProcessContents(self, processContents):
        self.processContents = processContents

    def setStyleElementDeclaration(self):
        '''set the element style.
            standard -- GED or local element
        '''
        self.style = 'standard'

    def setStyleElementReference(self):
        '''set the element style.
            ref -- element reference
        '''
        self.style = 'ref'

    def setStyleAnyElement(self):
        '''set the element style.
            anyElement -- <any> element wildcard
        '''
        self.name = 'any'
        self.style = 'anyElement'

    def setStyleRecursion(self):
        '''set the element style.
            recursion -- do lazy evaluation of element/type because
               the element contains an instance of itself.
        '''
        self.style = 'recursion'

    def unQualified(self):
        '''Do not qualify element.
        '''
        self.qualified = False

    def _getOccurs(self):
        return 'minOccurs=%s, maxOccurs=%s, nillable=%s' \
               % (self.min, self.max, self.nil)

    def _getProcessContents(self):
        return 'processContents="%s"' \
               % (self.processContents)

    def _getvalue(self):
        if self.style == 'standard':
            pname = '"%s"' %self.name
            if self.qualified is True:
                pname = '(ns,"%s")' %self.name
            return '%s(pname=%s, aname="%s", %s, encoded=kw.get("encoded"))' \
                   % (self.klass, pname,
                      self.getAttributeName(self.name), self._getOccurs())
        elif self.style == 'ref':
            return '%s(%s, encoded=kw.get("encoded"))' % (self.klass, self._getOccurs())
        elif self.style == 'anyElement':
            return 'ZSI.TC.AnyElement(aname="%s", %s, %s)' \
                %(self.getAttributeName(self.name), self._getOccurs(), self._getProcessContents())
        elif self.style == 'recursion':
            return 'ZSI.TC.AnyElement(aname="%s", %s, %s)' \
                % (self.getAttributeName(self.name), self._getOccurs(), self._getProcessContents())

    def __str__(self):
        return self._getvalue()
   
 
class RPCMessageTcListComponentContainer(TcListComponentContainer):
    '''Container for rpc/literal rpc/encoded message typecode.
    '''
    def __init__(self, qualified=True, encoded=None):
        '''
        encoded -- encoded namespaceURI, if None treat as rpc/literal.
        '''
        TcListComponentContainer.__init__(self, qualified=qualified)
        self._encoded = encoded
 
    def _getvalue(self):
        encoded = self._encoded
        if encoded is not None:
            encoded = '"%s"' %self._encoded

        if self.style == 'standard':
            pname = '"%s"' %self.name
            if self.qualified is True:
                pname = '(ns,"%s")' %self.name
            return '%s(pname=%s, aname="%s", encoded=%s, %s)' \
                   %(self.klass, pname, self.getAttributeName(self.name), 
                     encoded, self._getOccurs())
        elif self.style == 'ref':
            return '%s(encoded=%s, %s)' % (self.klass, encoded, self._getOccurs())
        elif self.style == 'anyElement':
            return 'ZSI.TC.AnyElement(aname="%s", %s, %s)' \
                %(self.getAttributeName(self.name), self._getOccurs(), self._getProcessContents())
        elif self.style == 'recursion':
            return 'ZSI.TC.AnyElement(aname="%s", %s, %s)' \
                % (self.getAttributeName(self.name), self._getOccurs(), self._getProcessContents())


class ElementSimpleTypeContainer(TypecodeContainerBase):

    type = DEC

    def setUp(self, tp):
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        qName = tp.getAttribute('type')
        self.sKlass = BTI.get_typeclass(qName[1], qName[0])
        self.pyclass = BTI.get_pythontype(None, None, typeclass=self.sKlass)

    def _setContent(self):
        aname = self.getAttributeName(self.name)
        pyclass = self.pyclass

        # bool cannot be subclassed
        if pyclass == 'bool': pyclass = 'int'

        element = [
            '%sclass %s(%s, ElementDeclaration):'\
                % (ID1, self.getClassName(), self.sKlass),
            '%s%s' % (ID2, self.literalTag()),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.simpleConstructor()),
            '%skw["pname"] = ("%s","%s")' % (ID3, self.ns, self.name),
            '%skw["aname"] = "%s"' % (ID3, aname),
        ]

        # TODO: What about getPyClass and getPyClassDefinition?
        #     I want to add pyclass metaclass here but this needs to be 
        #     corrected first.
        #
        # anyType (?others) has no pyclass.
        app = element.append
        if pyclass is not None:
            app('%sclass IHolder(%s): typecode=self' % (ID3, pyclass),)
            app('%skw["pyclass"] = IHolder' %(ID3),)
            app('%sIHolder.__name__ = "%s_immutable_holder"' %(ID3, aname),)

        app('%s%s' % (ID3, self.simpleConstructor(self.sKlass)),)

        self.writeArray(element)


class ElementLocalSimpleTypeContainer(TypecodeContainerBase):
    '''local simpleType container
    '''
    type = DEC 
    def _setContent(self):

        element = [
            '%sclass %s(%s, ElementDeclaration):' % (ID1, self.getClassName(),
                                                     self.sKlass),
            '%s%s' % (ID2, self.literalTag()),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.simpleConstructor()),
            '%skw["pname"] = ("%s","%s")' % (ID3, self.ns, self.name),
            '%skw["aname"] = "%s"' % (ID3, self.getAttributeName(self.name)),
            '%s%s' % (ID3, self.simpleConstructor(self.sKlass)),
            ]

        self.writeArray(element)

    def setUp(self, tp):
        assert tp.isElement() is True and tp.content is not None and \
            tp.content.isLocal() is True and tp.content.isSimple() is True ,\
            'expecting local simple type: %s' %tp.getItemTrace()

        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        content = tp.content.content
        if content.isRestriction():
            try:
                 base = content.getTypeDefinition()
            except SchemaError, ex:
                 base = None

            qName = content.getAttributeBase()
            if base is None:
                self.sKlass = BTI.get_typeclass(qName[1], qName[0])
                return

            raise Wsdl2PythonError, 'unsupported local simpleType restriction: %s' \
                %tp.content.getItemTrace()

        if content.isList():
            try:
                 base = content.getTypeDefinition()
            except SchemaError, ex:
                 base = None

            if base is None:
                qName = content.getItemType()
                self.sKlass = BTI.get_typeclass(qName[1], qName[0])
                return

            raise Wsdl2PythonError, 'unsupported local simpleType List: %s' \
                %tp.content.getItemTrace()

        if content.isUnion():
            raise Wsdl2PythonError, 'unsupported local simpleType Union: %s' \
                %tp.content.getItemTrace()

        raise Wsdl2PythonError, 'unexpected schema item: %s' \
            %tp.content.getItemTrace()


class ElementLocalComplexTypeContainer(TypecodeContainerBase, AttributeMixIn):

    type = DEC

    def setUp(self, tp):
        '''
        {'xsd':['annotation', 'simpleContent', 'complexContent',\
        'group', 'all', 'choice', 'sequence', 'attribute', 'attributeGroup',\
        'anyAttribute', 'any']}
        '''
        # JRB HACK SUPPORTING element/no content.
        assert tp.isElement() is True and \
            (tp.content is None or (tp.content.isComplex() is True and tp.content.isLocal() is True)),\
            'expecting element w/local complexType not: %s' %tp.content.getItemTrace()

        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()

        complex = tp.content
        # JRB HACK SUPPORTING element/no content.
        if complex is None:
            self.mgContent = ()
            return
        
        attributeContent = complex.getAttributeContent()

        self.mgContent = None
        if complex.content is None:
            self.mgContent = ()
        elif complex.content.isSimple():
            if complex.content.content.isExtension():
                # TODO: Not really supported just passing thru
                pass
            elif complex.content.content.isRestriction():
                # TODO: Not really supported just passing thru
                pass
            else:
                raise ContainerError,\
                   'not implemented local complexType/simpleContent: %s'\
                   %tp.getItemTrace()
        elif complex.content.isComplex() is True:
            if complex.content.content is None:
                self.mgContent = ()
            elif complex.content.content.isExtension() is True and\
                 complex.content.content.content is not None and\
                 complex.content.content.content.isModelGroup() is True:
                self.mgContent = complex.content.content.content.content
                attributeContent = \
                    complex.content.content.getAttributeContent()
            elif complex.content.content.isRestriction() is True and\
                 complex.content.content.content is not None and\
                 complex.content.content.content.isModelGroup() is True:
                self.mgContent = complex.content.content.content.content
                attributeContent = \
                    complex.content.content.getAttributeContent()
        elif complex.content.isModelGroup() is True:
            self.mgContent = complex.content.content

        if self.mgContent is None: 
            self.mgContent = ()
        assert type(self.mgContent) is tuple, 'XXX: %s' %self.mgContent.getItemTrace()

        self.attrComponents = self._setAttributes(attributeContent)
        
    def _setContent(self):

        element = [
            '%sclass %s(ZSI.TCcompound.ComplexType, ElementDeclaration):' \
            % (ID1,self.getClassName()),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.literalTag()),
            '%s%s' % (ID2, self.simpleConstructor()),
            #'%s' % self.getElements(),
            '%s%s' % (ID3, self.nsuriLogic()),
            '%sTClist = [%s]' % (ID3, self.getTypecodeList()),
            '%skw["pname"] = ("%s","%s")' % (ID3, self.ns, self.name),
            '%skw["aname"] = "%s"' % (ID3, self.getAttributeName(self.name)),
            ]
            
        element.append('%sself.%s = {}'%(ID3, AttributeMixIn.typecode))
        element.append(\
            '%(ID3)sZSI.TCcompound.ComplexType.__init__(self, None, TClist, inorder=0, **kw)' %KW
        )
        for l in self.attrComponents: element.append('%s%s'%(ID3, l))
                   
        # pyclass class definition
        element += self.getPyClassDefinition()

        # set pyclass
        kw = KW.copy()
        kw['pyclass'] = self.getPyClass()
        element.append('%(ID3)sself.pyclass = %(pyclass)s' %kw)  

        self.writeArray(element)
        
    
class ElementGlobalDefContainer(TypecodeContainerBase):

    type = DEC

    def setUp(self, element):
        self.name = element.getAttribute('name')
        self.ns = element.getTargetNamespace()

        tp = element.getTypeDefinition('type')
        self.sKlass = tp.getAttribute('name')
        self.sKlassNS = tp.getTargetNamespace()


    def _setContent(self):
        '''GED defines element name, so also define typecode aname
        '''
        element = [
            '%sclass %s(ElementDeclaration):' % (ID1, self.getClassName()),
            '%s%s' % (ID2, self.literalTag()),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.simpleConstructor()),
            '%skw["pname"] = ("%s","%s")' % (ID3, self.ns, self.name),
            '%skw["aname"] = "%s"' % (ID3, self.getAttributeName(self.name)),
            '%s'   % self.getBasesLogic(ID3),
            '%s%s.%s.__init__(self, **kw)' \
            % (ID3, NAD.getAlias(self.sKlassNS), type_class_name(self.sKlass) ),
            '%sself.pyclass.__name__ = "%s_Holder"' %(ID3, self.getClassName()),
            ]

        self.writeArray(element)


class ComplexTypeComplexContentContainer(TypecodeContainerBase, AttributeMixIn):
    '''Represents ComplexType with ComplexContent.
    '''
    type = DEF

    def __init__(self, do_extended=False):
        '''
        restriction
        extension
        extType -- used in figuring attrs for extensions
        '''
        TypecodeContainerBase.__init__(self, do_extended=do_extended)
        self.restriction = False
        self.extension = False
        self.extType = None
        self._is_array = False
        self._kw_array = None

    def setUp(self, tp):
        '''complexContent/[extension,restriction]
        '''
        assert tp.content.isComplex() is True and \
            (tp.content.content.isRestriction() or tp.content.content.isExtension() is True),\
            'expecting complexContent/[extension,restriction]'

        attributeContent = ()
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        derivation = tp.content.content
        try:
            base = derivation.getTypeDefinition('base')
        except XMLSchema.SchemaError, ex:
            base = None

        if base is None:
            # SOAP-ENC:Array expecting arrayType attribute reference
            qname = derivation.getAttributeQName('base')
            if qname is None:
                raise ContainerError, 'No arrayType declared for Array: %s'\
                    %derivation.getItemTrace()

            self.sKlass = BTI.get_typeclass(qname[1], qname[0])
            self.sKlassNS = qname[0]

            self._is_array = True
            self._kw_array = {'atype':None, 'id3':ID3, 'ofwhat':None}
            attr = None
            for a in derivation.getAttributeContent():
                assert a.isAttribute() is True,\
                    'only attribute content expected: %s' %a.getItemTrace()

                if a.isReference() is True:
                    if a.getAttribute('ref') == (SOAP.ENC,'arrayType'):
                        self._kw_array['atype'] = a.getAttributeQName((WSDL.BASE, 'arrayType'))
                        attr = a
                        break

            qname = self._kw_array.get('atype')
            if attr is not None:
                qname = self._kw_array.get('atype')
                ncname = qname[1].strip('[]')
                namespace = qname[0]
                try:
                    ofwhat = attr.getSchemaItem(XMLSchema.TYPES, namespace, ncname)
                except XMLSchema.SchemaError, ex:
                    ofwhat = None

                if ofwhat is None:
                    self._kw_array['ofwhat'] = BTI.get_typeclass(ncname, namespace)
                else:
                    self._kw_array['ofwhat'] = GetClassNameFromSchemaItem(ofwhat, do_extended=self.do_extended)

                if self._kw_array['ofwhat'] is None:
                    raise ContainerError, 'For Array could not resolve ofwhat typecode(%s,%s): %s'\
                        %(namespace, ncname, derivation.getItemTrace())
       
        else:
            self.sKlass = base.getAttribute('name')
            self.sKlassNS = base.getTargetNamespace()

        if derivation.isRestriction():
            self.restriction = True
            self.extension = False
            if hasattr(tp, 'getAttributeContent'):
                attributeContent = tp.getAttributeContent()
        elif derivation.isExtension():
            self.restriction = False
            self.extension = True
            attrs = []
            if hasattr(tp, 'getAttributeContent') and \
                tp.getAttributeContent() != None:
                attrs += tp.getAttributeContent()
            if hasattr(derivation, 'getAttributeContent') and \
                derivation.getAttributeContent():
                attrs += derivation.getAttributeContent()
            if attrs:
                attributeContent = attrs
                self.extType = derivation
        else:
            raise Wsdl2PythonError, 'neither restriction nor extension?'

        if derivation.content is not None \
            and derivation.content.isModelGroup():
            group = derivation.content
            if group.isReference():
                group = group.getModelGroupReference()
            self.mgContent = group.content
        elif derivation.content:
            raise Wsdl2PythonError, \
                'expecting model group, not: %s' %derivation.content.getItemTrace()
        else:
            self.mgContent = ()

        self.attrComponents = self._setAttributes(attributeContent)
        
    def _setContent(self):
        '''JRB What is the difference between instance data
        ns, name, -- type definition?
        sKlass, sKlassNS? -- element declaration?
        '''
        definition = []
        if self._is_array is True:
            # 
            # SOAP-ENC:Array
            if _is_xsd_or_soap_ns(self.sKlassNS) is False and self.sKlass == 'Array':
                raise ContainerError, 'unknown type: (%s,%s)'\
                    %(self.sKlass, self.sKlassNS)
            definition.append(\
                '%sclass %s(ZSI.TC.Array, TypeDefinition):' % (ID1, self.getClassName()),
            )
            definition.append(\
                '%s%s' % (ID2, self.schemaTag()),
            )
            definition.append(\
                '%s%s' % (ID2, self.typeTag()),
            )
            definition.append(\
                '%s%s' % (ID2, self.pnameConstructor()),
            )
            # No need to xsi:type array items since specify with
            # SOAP-ENC:arrayType attribute.
            definition.append(\
                '%(id3)sofwhat = %(ofwhat)s(None, typed=False)' %self._kw_array,
            )
            definition.append(\
                '%(id3)satype = %(atype)s' %self._kw_array,
            )
            definition.append(\
                '%s%s.__init__(self, atype, ofwhat, pname=pname, childnames=\'item\', **kw)'
                %(ID3, self.sKlass),
            )
        else:
            definition.append(\
                '%sclass %s(TypeDefinition):' % (ID1, self.getClassName()),
            )
            definition.append(\
                '%s%s' % (ID2, self.schemaTag()),
            )
            definition.append(\
                '%s%s' % (ID2, self.typeTag()),
            )
            definition.append(\
                '%s%s' % (ID2, self.pnameConstructor()),
            )
            definition.append(\
                '%s%s' % (ID3, self.nsuriLogic()),
            )
            definition.append(\
                '%sTClist = [%s]' % (ID3, self.getTypecodeList()),
            )
            definition.append(\
                '%s'   % self.getBasesLogic(ID3),
            )
            definition.append('%sself.%s = {}'%(ID3, AttributeMixIn.typecode))
            definition.append(\
                '%s%s.%s.__init__(self, pname, **kw)' \
                %(ID3, NAD.getAlias(self.sKlassNS), type_class_name(self.sKlass) ),
            )
            if self.restriction:
                definition.append(\
                    '%sself.ofwhat = tuple(TClist)' %ID3,
                ) 
            else:
                definition.append(\
                    '%sself.ofwhat += tuple(TClist)' %ID3,
                ) 

        for l in self.attrComponents: definition.append('%s%s'%(ID3, l))
        self.writeArray(definition)



class ComplexTypeContainer(TypecodeContainerBase, AttributeMixIn):
    '''Represents a global complexType definition.
    '''
    type = DEF

    def setUp(self, tp, empty=False):
        '''Problematic, loose all model group information.
        <all>, <choice>, <sequence> ..

           tp -- type definition
           empty -- no model group, just use as a dummy holder.
        '''
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.mixed = tp.isMixed()
        self.mgContent = ()
        
        if empty is True or tp.content is None:
            pass

        elif tp.content.isReference() is True: 
            ref = tp.content.getModelGroupReference()
            if ref.content.content is not None:
               self.mgContent = ref.content.content
        elif tp.content.content is not None:
            self.mgContent = tp.content.content

        self.attrComponents = self._setAttributes(tp.getAttributeContent())
        
    def _setContent(self):
        definition = [
            '%sclass %s(ZSI.TCcompound.ComplexType, TypeDefinition):'
            % (ID1, self.getClassName()),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.typeTag()),
            '%s%s' % (ID2, self.pnameConstructor()),
            #'%s'   % self.getElements(),
            '%s%s' % (ID3, self.nsuriLogic()),
            '%sTClist = [%s]' % (ID3, self.getTypecodeList()),
            ]

        definition.append('%sself.%s = {}'%(ID3, AttributeMixIn.typecode))
        definition.append(\
            '%sZSI.TCcompound.ComplexType.__init__(self, None, TClist, pname=pname, inorder=0, %s**kw)' \
            %(ID3, self.getExtraFlags())
        )
        
        #self._setAttributes()
        for l in self.attrComponents: definition.append('%s%s'%(ID3, l))

        # pyclass class definition
        definition += self.getPyClassDefinition()

        # set pyclass
        kw = KW.copy()
        kw['pyclass'] = self.getPyClass()
        definition.append('%(ID3)sself.pyclass = %(pyclass)s' %kw)
        self.writeArray(definition)


class SimpleTypeContainer(TypecodeContainerBase):
    type = DEF

    def __init__(self):
        '''
        Instance Data From TypecodeContainerBase NOT USED...
           mgContent
        '''
        TypecodeContainerBase.__init__(self)

    def setUp(self, tp):
        raise NotImplementedError, 'abstract method not implemented'

    def _setContent(self, tp):
        raise NotImplementedError, 'abstract method not implemented'

    def getPythonType(self):
        pyclass = eval(str(self.sKlass))
        if issubclass(pyclass, ZSI.TC.String):
            return 'str'
        if issubclass(pyclass, ZSI.TC.Ilong) or issubclass(pyclass, ZSI.TC.IunsignedLong):
            return 'long'
        if issubclass(pyclass, ZSI.TC.Boolean) or issubclass(pyclass, ZSI.TC.Integer):
            return 'int'
        if issubclass(pyclass, ZSI.TC.Decimal):
            return 'float'
        if issubclass(pyclass, ZSI.TC.Gregorian) or issubclass(pyclass, ZSI.TC.Duration):
            return 'tuple'
        return None

    def getPyClassDefinition(self):
        definition = []
        pt = self.getPythonType()
        if pt is not None:
            definition.append('%sclass %s(%s):' %(ID3,self.getPyClass(),pt))
            definition.append('%stypecode = self' %ID4)
        return definition


class RestrictionContainer(SimpleTypeContainer):
    '''
       simpleType/restriction
    '''

    def setUp(self, tp):
        assert tp.isSimple() is True and tp.isDefinition() is True and \
            tp.content.isRestriction() is True,\
            'expecting simpleType restriction, not: %s' %tp.getItemTrace()

        if tp.content is None:
            raise Wsdl2PythonError, \
                  'empty simpleType defintion: %s' %tp.getItemTrace()

        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.sKlass = None

        base = tp.content.getAttribute('base')
        if base is not None:
            try:
                item = tp.content.getTypeDefinition('base')
            except SchemaError, ex:
                pass

            if item is None:
                self.sKlass = BTI.get_typeclass(base[1], base[0])
                return

            raise Wsdl2PythonError, \
                'Not Supporting simpleType/Restriction w/User-Defined Base: %s %s' %(tp.getItemTrace(),item.getItemTrace())

        sc = tp.content.getSimpleTypeContent()
        if sc is not None and True is sc.isSimple() is sc.isLocal() is sc.isDefinition():
            base = None
            if sc.content.isRestriction() is True:
                try:
                    item = tp.content.getTypeDefinition('base')
                except SchemaError, ex:
                    pass

                if item is None:
                    base = sc.content.getAttribute('base')
                    if base is not None:
                        self.sKlass = BTI.get_typeclass(base[1], base[0])
                        return
                    raise Wsdl2PythonError, \
                        'Not Supporting simpleType/Restriction w/User-Defined Base: '\
                        %item.getItemTrace()

                raise Wsdl2PythonError, \
                    'Not Supporting simpleType/Restriction w/User-Defined Base: '\
                    %item.getItemTrace()

            if sc.content.isList() is True:
                raise Wsdl2PythonError, \
                      'iction base in subtypes: %s'\
                      %sc.getItemTrace()

            if sc.content.isUnion() is True:
                raise Wsdl2PythonError, \
                      'could not get restriction base in subtypes: %s'\
                      %sc.getItemTrace()

            return

        raise Wsdl2PythonError, 'No Restriction @base/simpleType: %s' %tp.getItemTrace()

    def _setContent(self):

        definition = [
            '%sclass %s(%s, TypeDefinition):' %(ID1, self.getClassName(), 
                         self.sKlass),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.typeTag()),
            '%s%s' % (ID2, self.pnameConstructor()),
        ]
        if self.getPythonType() is None:
            definition.append('%s%s.__init__(self, pname, **kw)' %(ID3,
                               self.sKlass))
        else:
            definition.append('%s%s.__init__(self, pname, pyclass=None, **kw)' \
                               %(ID3, self.sKlass,))
          
            # pyclass class definition
            definition += self.getPyClassDefinition()
                
            # set pyclass
            kw = KW.copy()
            kw['pyclass'] = self.getPyClass()
            definition.append('%(ID3)sself.pyclass = %(pyclass)s' %kw)    

        self.writeArray(definition)


class ComplexTypeSimpleContentContainer(SimpleTypeContainer, AttributeMixIn):
    '''Represents a ComplexType with simpleContent.
    '''
    type = DEF

    def setUp(self, tp):
        '''tp -- complexType/simpleContent/[Exention,Restriction]
        '''
        assert tp.isComplex() is True and tp.content.isSimple() is True,\
            'expecting complexType/simpleContent not: %s' %tp.content.getItemTrace()

        simple = tp.content
        dv = simple.content
        assert dv.isExtension() is True or dv.isRestriction() is True,\
            'expecting complexType/simpleContent/[Extension,Restriction] not: %s' \
            %tp.content.getItemTrace()

        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        # TODO: Why is this being set?
        self.content.attributeContent = dv.getAttributeContent()
        
        base = dv.getAttribute('base')
        if base is not None:
            self.sKlass = BTI.get_typeclass( base[1], base[0] )
            if not self.sKlass:
                self.sKlass,self.sKlassNS = base[1], base[0]
                
            self.attrComponents = self._setAttributes(
                                      self.content.attributeContent
                                      )
            return

        raise Wsdl2PythonError,\
            'simple content derivation bad base attribute: ' %tp.getItemTrace()

    def _setContent(self):
        if type(self.sKlass) in (types.ClassType, type):
            definition = [
                '%sclass %s(%s, TypeDefinition):' \
                % (ID1, self.getClassName(), self.sKlass),
                '%s%s' % (ID2, self.schemaTag()),
                '%s%s' % (ID2, self.typeTag()),
                '%s%s' % (ID2, self.pnameConstructor()),
                ]
    
            if self.getPythonType() is None:
                definition.append('%sself.%s = {}'%(ID3, AttributeMixIn.typecode))
                definition.append('%s%s.__init__(self, pname, **kw)' %(ID3, self.sKlass))
            else:
                definition.append('%sself.%s = {}'%(ID3, AttributeMixIn.typecode))
                definition.append(\
                    '%s%s.__init__(self, pname, pyclass=None, **kw)'\
                    %(ID3, self.sKlass)
                )
              
                # pyclass class definition
                definition += self.getPyClassDefinition()
                    
                # set pyclass
                kw = KW.copy()
                kw['pyclass'] = self.getPyClass()
                definition.append('%(ID3)sself.pyclass = %(pyclass)s' %kw)    
        
        else:
            definition = [
                '%sclass %s(TypeDefinition):' % (ID1, self.getClassName()),
                '%s%s' % (ID2, self.schemaTag()),
                '%s%s' % (ID2, self.typeTag()),
                '%s%s' % (ID2, self.pnameConstructor()),
                '%s%s' % (ID3, self.nsuriLogic()),
                '%s'   % self.getBasesLogic(ID3),
                '%sself.%s = {}'%(ID3, AttributeMixIn.typecode),
                '%s%s.%s.__init__(self, pname, **kw)' \
                % (ID3, NAD.getAlias(self.sKlassNS), type_class_name(self.sKlass) ),
                ]

        for l in self.attrComponents: definition.append('%s%s'%(ID3, l))
        self.writeArray(definition)



class UnionContainer(SimpleTypeContainer):
    '''SimpleType Union
    '''
    type = DEF

    def __init__(self):
        SimpleTypeContainer.__init__(self)
        self.memberTypes = None

    def setUp(self, tp):
        if tp.content.isUnion() is False:
            raise ContainerError, 'content must be a Union: %s' %tp.getItemTrace()
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.sKlass = 'ZSI.TC.Union'
        self.memberTypes = tp.content.getAttribute('memberTypes')

    def _setContent(self):
        definition = [
            '%sclass %s(%s, TypeDefinition):' \
            % (ID1, self.getClassName(), self.sKlass),
            '%smemberTypes = %s' % (ID2, self.memberTypes),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.typeTag()),
            '%s%s' % (ID2, self.pnameConstructor()),
            '%s%s' % (ID3, self.pnameConstructor(self.sKlass)),
            ]
        self.writeArray(definition)


class ListContainer(SimpleTypeContainer):
    '''SimpleType List
    '''
    type = DEF

    def setUp(self, tp):
        if tp.content.isList() is False:
            raise ContainerError, 'content must be a List: %s' %tp.getItemTrace()
        self.name = tp.getAttribute('name')
        self.ns = tp.getTargetNamespace()
        self.sKlass = 'ZSI.TC.List'
        self.itemType = tp.content.getAttribute('itemType')

    def _setContent(self):
        definition = [
            '%sclass %s(%s, TypeDefinition):' \
            % (ID1, self.getClassName(), self.sKlass),
            '%sitemType = %s' % (ID2, self.itemType),
            '%s%s' % (ID2, self.schemaTag()),
            '%s%s' % (ID2, self.typeTag()),
            '%s%s' % (ID2, self.pnameConstructor()),
            '%s%s' % (ID3, self.pnameConstructor(self.sKlass)),
            ]
        self.writeArray(definition)

