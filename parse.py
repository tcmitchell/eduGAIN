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

    def toXML(self):
        return '<Include>%s</Include>' % (self.entityID)


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
        self.includeEntities = list()

    def endDocument(self):
        self.includeEntities.sort()
        for entity in self.includeEntities:
            print entity.toXML()

    def startElement(self, name, attrs):
        if name.endswith(InCommonHandler.ENTITY_DESCRIPTOR):
            if self.currentEntity:
                print 'ERROR: currentEntity already defined'
            # print 'startElement(%r, %r)' % (name, attrs)
            entityID = attrs.getValue('entityID')
            #print 'entity: %s' % (entityID)
            self.currentEntity = Entity(entityID)
        elif name.endswith(InCommonHandler.ATTRIBUTE_VALUE):
            #print 'attribute value'
            self.inAttributeValue = True
        elif name.endswith(InCommonHandler.IDP_DESCRIPTOR):
            self.currentEntity.isIDP = True

    def endElement(self, name):
        if name.endswith(InCommonHandler.ENTITY_DESCRIPTOR):
            #print 'endElement(%r)' % (name)
            self.closeEntity()
        elif name.endswith(InCommonHandler.ATTRIBUTE_VALUE):
            self.inAttributeValue = False

    def characters(self, content):
        if self.inAttributeValue and content == InCommonHandler.REG_INCOMMON:
            self.currentEntity.isInCommon = True

    def closeEntity(self):
        if self.currentEntity.isValid():
            self.includeEntities.append(self.currentEntity)
        self.currentEntity = None


class ShibbolethHandler(xml.sax.handler.ContentHandler):
    """Parse a shibboleth2.xml file and gather the whitelist
    include entities.
    """
    METADATA_FILTER = u'MetadataFilter'
    INCLUDE = u'Include'
    ATTR_TYPE = u'type'
    VALUE_WHITELIST = u'Whitelist'

    def __init__(self):
        self.inWhitelist = False
        self.inInclude = False
        self.includedEntities = set()

    def startElement(self, name, attrs):
        if (name.endswith(ShibbolethHandler.METADATA_FILTER)
                and ShibbolethHandler.ATTR_TYPE in attrs.getNames()
                and (attrs.getValue(ShibbolethHandler.ATTR_TYPE)
                         == ShibbolethHandler.VALUE_WHITELIST)):
            self.inWhitelist = True
        elif self.inWhitelist and name.endswith(ShibbolethHandler.INCLUDE):
            self.inInclude = True

    def endElement(self, name):
        if self.inWhitelist and name.endswith(ShibbolethHandler.METADATA_FILTER):
            self.inWhitelist = False
        elif self.inInclude and name.endswith(ShibbolethHandler.INCLUDE):
            self.inInclude = False

    def characters(self, content):
        if self.inWhitelist and self.inInclude:
            self.includedEntities.add(content)


if __name__ == '__main__':
    handler = InCommonHandler()
    errorHandler = RaiseErrorHandler()
    #xml.sax.parse(sys.argv[1], handler, errorHandler)
    handler = ShibbolethHandler()
    xml.sax.parse(sys.argv[2], handler, errorHandler)
    print 'Found %d included entities' % (len(handler.includedEntities))

# xml.sax.parse('InCommon-metadata-preview.xml', handler)
