# Copyright (c) 2001 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.

from ZSI import *
from ZSI.client import *
from ZSI.typeinterpreter import BaseTypeInterpreter
import wstools
from wstools.Utility import DOM
from urlparse import urlparse
import weakref

class ServiceProxy:
    """A ServiceProxy provides a convenient way to call a remote web
       service that is described with WSDL. The proxy exposes methods
       that reflect the methods of the remote web service."""

    def __init__(self, wsdl, service=None, port=None, tracefile=None,
                 typesmodule=None, nsdict=None, soapAction=None, ns=None, op_ns=None, use_wsdl=False):
        """
        Instance data
           use_wsdl -- if True try to construct XML Instance from 
                   information in WSDL.
        """
        if not hasattr(wsdl, 'targetNamespace'):
            wsdl = wstools.WSDLTools.WSDLReader().loadFromURL(wsdl)

#        for item in wsdl.types.items():
#            self._serializer.loadSchema(item)

        self._service = wsdl.services[service or 0]
        self.__doc__ = self._service.documentation
        self._port = self._service.ports[port or 0]
        self._name = self._service.name
        self._wsdl = wsdl
        self._tracefile = tracefile
        self._typesmodule = typesmodule
        self._nsdict = nsdict
        self._soapAction = soapAction
        self._ns = ns
        self._op_ns = op_ns
        self._use_wsdl = use_wsdl
        
        binding = self._port.getBinding()
        portType = binding.getPortType()
        for item in portType.operations:
            callinfo = wstools.WSDLTools.callInfoFromWSDL(self._port, item.name)
            method = MethodProxy(self, callinfo)
            setattr(self, item.name, method)

    def _call(self, name, *args, **kwargs):
        """Call the named remote web service method."""
        if len(args) and len(kwargs):
            raise TypeError(
                'Use positional or keyword argument only.'
                )

        callinfo = getattr(self, name).callinfo
        soapAction = callinfo.soapAction
        url = callinfo.location
        (protocol, host, uri, query, fragment, identifier) = urlparse(url)
        port = '80'
        if host.find(':') >= 0:
            host, port = host.split(':')

        binding = Binding(host=host, tracefile=self._tracefile,
                          ssl=(protocol == 'https'),
                          port=port, url=None, typesmodule=self._typesmodule,
                          nsdict=self._nsdict, soapaction=self._soapAction,
                          ns=self._ns, op_ns=self._op_ns)

        if self._use_wsdl:
            request, response = self._getTypeCodes(callinfo)
            if len(kwargs): args = kwargs
            binding.Send(url=uri, opname=None, obj=args,
                         nsdict=self._nsdict, soapaction=soapAction, requesttypecode=request)
            return binding.Receive(replytype=response)

        apply(getattr(binding, callinfo.methodName), args)

        return binding.Receive()

    def _getTypeCodes(self, callinfo):
        """Returns typecodes representing input and output messages
           callinfo --  WSDLTools.SOAPCallInfo instance describing an operation.
        """
        prefix = None
        self._resetPrefixDict()
        if callinfo.use == 'encoded':
            prefix = self._getPrefix(callinfo.namespace)
        requestTC = self._getTypeCode(parameters=callinfo.getInParameters(), literal=(callinfo.use=='literal'))

        self._resetPrefixDict()
        replyTC = self._getTypeCode(parameters=callinfo.getOutParameters(), literal=(callinfo.use=='literal'))
        
        if callinfo.style == 'rpc':
            request = TC.Struct(pyclass=None, ofwhat=requestTC, pname=callinfo.methodName)
            response = TC.Struct(pyclass=None, ofwhat=replyTC, pname='%sResponse' %callinfo.methodName)
        else:
            request = requestTC[0]
            response = replyTC[0]

        #THIS IS FOR RPC/ENCODED, DOC/ENCODED Wrapper
        if prefix and callinfo.use == 'encoded':
            request.oname = '%(prefix)s:%(name)s xmlns:%(prefix)s="%(namespaceURI)s"' \
                %{'prefix':prefix, 'name':request.oname, 'namespaceURI':callinfo.namespace}

        return request, response

    def _getTypeCode(self, parameters, literal=False):
        """Returns typecodes representing a parameter set
           parameters -- list of WSDLTools.ParameterInfo instances representing
              the parts of a WSDL Message.
        """
        ofwhat = []
        for part in parameters:
            namespaceURI,localName = part.type

            if part.element_type:
                #global element
                element = self._wsdl.types[namespaceURI].elements[localName]
                tc = self._getElement(element, literal=literal, local=False, namespaceURI=namespaceURI)
            else:
                #local element
                name = part.name
                typeClass = self._getTypeClass(namespaceURI, localName)
                if not typeClass:
                    self._wsdl.types[namespaceURI].getTypeDefinition(localName)
                    typeClass = self._getElement()
                tc = typeClass(name)
            ofwhat.append(tc)
        return ofwhat

    def _globalElement(self, typeCode, namespaceURI, literal):
        """namespaces typecodes representing global elements with 
             literal encoding.
           typeCode -- typecode representing an element.
           namespaceURI -- namespace 
           literal -- True/False
        """
        if literal:
            typeCode.oname = '%(prefix)s:%(name)s xmlns:%(prefix)s="%(namespaceURI)s"' \
                %{'prefix':self._getPrefix(namespaceURI), 'name':typeCode.oname, 'namespaceURI':namespaceURI}

    def _getPrefix(self, namespaceURI):
        """Retrieves a prefix/namespace mapping.
           namespaceURI -- namespace 
        """
        prefixDict = self._getPrefixDict()
        if prefixDict.has_key(namespaceURI):
            prefix = prefixDict[namespaceURI]
        else:
            prefix = 'ns1'
            while prefix in prefixDict.values():
                prefix = 'ns%d' %int(prefix[-1]) + 1
            prefixDict[namespaceURI] = prefix
        return prefix

    def _getPrefixDict(self):
        """Used to hide the actual prefix dictionary.
        """
        if not hasattr(self, '_prefixDict'):
            self.__prefixDict = {}
        return self.__prefixDict

    def _resetPrefixDict(self):
        """Clears the prefix dictionary, this needs to be done 
           before creating a new typecode for a message 
           (ie. before, and after creating a new message typecode)
        """
        self._getPrefixDict().clear()

    def _getElement(self, element, literal=False, local=False, namespaceURI=None):
        """Returns a typecode instance representing the passed in element.
           element -- XMLSchema.ElementDeclaration instance
           literal -- literal encoding?
           local -- is locally defined?
           namespaceURI -- namespace
        """
        if not element.isElement():
            raise TypeError, 'Expecting an ElementDeclaration'

        tc = None
        ofwhat = []

        elementName = element.getAttribute('name')
        tp = element.getTypeDefinition('type')

        if not (tp or element.content):
            nsuriType,localName = element.getAttribute('type')
            minOccurs = element.getAttribute('minOccurs')
            maxOccurs = element.getAttribute('maxOccurs')
            typeClass = self._getTypeClass(nsuriType,localName)
            return typeClass(elementName, repeatable=maxOccurs>1, optional=not minOccurs)
        elif not tp:
            tp = element.content

        if not (tp.isDefinition() and tp.isComplex()):
            raise EvaluationError, 'only supporting complexType definition'
        elif not tp.content.isModelGroup():
            raise EvaluationError, 'only supporting a model group, no derivations'

        modelGroup = tp.content
        for item in modelGroup.content:
            ofwhat.append(self._getElement(item, literal=literal, local=True))

        tc = TC.Struct(pyclass=None, ofwhat=ofwhat, pname=elementName)
        if not local:
            self._globalElement(tc, namespaceURI=namespaceURI, literal=literal)
        return tc
    
    def _getTypeClass(self, namespaceURI, localName):
        """Returns a typecode class representing the type we are looking for.
           localName -- name of the type we are looking for.
           namespaceURI -- defining XMLSchema targetNamespace.
        """
        bti = BaseTypeInterpreter()
        simpleTypeClass = bti.get_typeclass(localName, namespaceURI)
        return simpleTypeClass


class MethodProxy:
    """ """
    def __init__(self, parent, callinfo):
        self.__name__ = callinfo.methodName
        self.__doc__ = callinfo.documentation
        self.callinfo = callinfo
        self.parent = weakref.ref(parent)

    def __call__(self, *args, **kwargs):
        return self.parent()._call(self.__name__, *args, **kwargs)
