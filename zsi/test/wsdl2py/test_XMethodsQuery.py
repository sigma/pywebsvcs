#!/usr/bin/env python

############################################################################
# David W. Robertson, LBNL
# See LBNLCopyright for copyright notice!
###########################################################################
import unittest
from ServiceTest import ServiceTestCase, ServiceTestSuite

"""
Unittest for contacting the XMethodsQuery Web service.

WSDL:  http://www.xmethods.net/wsdl/query.wsdl
"""

# General targets
def dispatch():
    """Run all dispatch tests"""
    suite = ServiceTestSuite()
    suite.addTest(unittest.makeSuite(XMethodsQueryTest, 'test_dispatch'))
    return suite

def local():
    """Run all local tests"""
    suite = ServiceTestSuite()
    suite.addTest(unittest.makeSuite(XMethodsQueryTest, 'test_local'))
    return suite

def net():
    """Run all network tests"""
    suite = ServiceTestSuite()
    suite.addTest(unittest.makeSuite(XMethodsQueryTest, 'test_net'))
    return suite
    
def all():
    """Run all tests"""
    suite = ServiceTestSuite()
    suite.addTest(unittest.makeSuite(XMethodsQueryTest, 'test_'))
    return suite


class XMethodsQueryTest(ServiceTestCase):
    """Test case for XMethodsQuery Web service
    """
    name = "test_XMethodsQuery"
    client_file_name = "XMethodsQuery_services.py"
    types_file_name = "XMethodsQuery_services_types.py"
    server_file_name = "XMethodsQuery_services_server.py"

    def test_net_getAllServiceNames(self):
        loc = self.client_module.XMethodsQueryLocator()
        port = loc.getXMethodsQuerySoapPortType(**self.getPortKWArgs())
        
        msg = self.client_module.getAllServiceNames2SoapIn()
        rsp = port.getAllServiceNames(msg)

    def test_net_getAllServiceSummaries(self):
        loc = self.client_module.XMethodsQueryLocator()
        port = loc.getXMethodsQuerySoapPortType(**self.getPortKWArgs())
        
        msg = self.client_module.getAllServiceSummaries1SoapIn()
        rsp = port.getAllServiceSummaries(msg)
        
    def test_net_getServiceDetail(self):
        loc = self.client_module.XMethodsQueryLocator()
        port = loc.getXMethodsQuerySoapPortType(**self.getPortKWArgs())
        
        msg = self.client_module.getServiceDetail4SoapIn()
        msg._id = 'uuid:A29C0D6C-5529-0D27-A91A-8E02D343532B'
        rsp = port.getServiceDetail(msg)
    
    def test_net_getServiceNamesByPublisher(self):
        loc = self.client_module.XMethodsQueryLocator()
        port = loc.getXMethodsQuerySoapPortType(**self.getPortKWArgs())
        
        msg = self.client_module.getServiceNamesByPublisher3SoapIn()
        msg._publisherID = 'xmethods.net'
        rsp = port.getServiceNamesByPublisher(msg)
    
    def test_net_getServiceSummariesByPublisher(self):
        loc = self.client_module.XMethodsQueryLocator()
        port = loc.getXMethodsQuerySoapPortType(**self.getPortKWArgs())
        
        msg = self.client_module.getServiceSummariesByPublisher0SoapIn()
        msg._publisherID = 'xmethods.net'
        rsp = port.getServiceSummariesByPublisher(msg)


if __name__ == "__main__" :
    unittest.TestProgram(defaultTest="makeTestSuite")
