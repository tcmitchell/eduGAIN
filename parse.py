import sys
import xml.sax

#----------------------------------------------------------------------
# To Do:
#
# Handle hide-from-discovery IdPs
#----------------------------------------------------------------------

class Entity(object):
    def __init__(self, id):
        self.entityID = id
        self.isIDP = False
        self.isInCommon = False
        self.hideFromDiscovery = False

    def isValid(self):
        return self.isIDP and self.isInCommon and not self.hideFromDiscovery


class RaiseErrorHandler(xml.sax.handler.ErrorHandler):
    """Raises all errors as exceptions to halt processing.
    Warnings are ignored.
    """
    def __init__(self):
        pass
    def error(self, exception):
        raise exception
    def fatalError(self, exception):
        raise exception
    def warning(self, exception):
        pass


class InCommonHandler(xml.sax.handler.ContentHandler):
    ENTITY_DESCRIPTOR = u'EntityDescriptor'
    ATTRIBUTE_VALUE = u'AttributeValue'
    IDP_DESCRIPTOR = u'IDPSSODescriptor'
    REG_INCOMMON = u'http://id.incommon.org/category/registered-by-incommon'
    HIDE_DISCOVERY = u'http://refeds.org/category/hide-from-discovery'

    def __init__(self):
        self.currentEntity = None
        self.inAttributeValue = False
        self.isIDP = False
        self.isInCommon = False
        self.includeEntities = list()

    def endDocument(self):
        self.includeEntities.sort()
        for entity in self.includeEntities:
            print '<Include>%s</Include>' % (entity)

    def startElement(self, name, attrs):
        if name.endswith(InCommonHandler.ENTITY_DESCRIPTOR):
            if self.currentEntity:
                print 'ERROR: currentEntity already defined'
            # print 'startElement(%r, %r)' % (name, attrs)
            entityID = attrs.getValue('entityID')
            #print 'entity: %s' % (entityID)
            self.currentEntity = entityID
        elif name.endswith(InCommonHandler.ATTRIBUTE_VALUE):
            #print 'attribute value'
            self.inAttributeValue = True
        elif name.endswith(InCommonHandler.IDP_DESCRIPTOR):
            self.isIDP = True

    def endElement(self, name):
        if name.endswith(InCommonHandler.ENTITY_DESCRIPTOR):
            #print 'endElement(%r)' % (name)
            self.closeEntity()
        elif name.endswith(InCommonHandler.ATTRIBUTE_VALUE):
            self.inAttributeValue = False

    def characters(self, content):
        if self.inAttributeValue and content == InCommonHandler.REG_INCOMMON:
            self.isInCommon = True

    def closeEntity(self):
        if self.currentEntity and self.isIDP and self.isInCommon:
            self.includeEntities.append(self.currentEntity)
        self.currentEntity = None
        self.isIDP = False
        self.isInCommon = False


if __name__ == '__main__':
    handler = InCommonHandler()
    errorHandler = RaiseErrorHandler()
    xml.sax.parse(sys.argv[1], handler, errorHandler)

# xml.sax.parse('InCommon-metadata-preview.xml', handler)
