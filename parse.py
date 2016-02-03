import smtplib
import sys
import xml.sax
from email.mime.text import MIMEText

#----------------------------------------------------------------------
# To Do:
#
# Handle hide-from-discovery IdPs
#----------------------------------------------------------------------
#
# python parse.py /var/run/shibboleth/InCommon-metadata.xml \
#                /etc/shibboleth/shibboleth2.xml
#
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
        self.includeEntities = set()

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
            self.AVcontent = ''
        elif name.endswith(InCommonHandler.IDP_DESCRIPTOR):
            self.currentEntity.isIDP = True

    def endElement(self, name):
        if name.endswith(InCommonHandler.ENTITY_DESCRIPTOR):
            #print 'endElement(%r)' % (name)
            self.closeEntity()
        elif name.endswith(InCommonHandler.ATTRIBUTE_VALUE):
            if self.AVcontent and self.AVcontent == InCommonHandler.REG_INCOMMON:
                self.currentEntity.isInCommon = True
            if self.AVcontent and self.AVcontent == InCommonHandler.HIDE_DISCOVERY:
                self.currentEntity.hideFromDiscovery = True
            self.AVcontent = ''
            self.inAttributeValue = False

    def characters(self, content):
        # Accumulate the content because it may not arrive at one time,
        # but over separate calls. See the xml.sax docs for more info.
        if self.inAttributeValue:
            self.AVcontent = self.AVcontent + content

    def closeEntity(self):
        if self.currentEntity.isValid():
            self.includeEntities.add(self.currentEntity.entityID)
        self.currentEntity = None


class ShibbolethHandler(xml.sax.handler.ContentHandler):
    """Parse a shibboleth2.xml file and gather the whitelist
    include entities.
    """
    METADATA_PROVIDER = u'MetadataProvider'
    METADATA_FILTER = u'MetadataFilter'
    INCLUDE = u'Include'
    ATTR_URI = u'uri'
    ATTR_TYPE = u'type'
    VALUE_WHITELIST = u'Whitelist'
    INCOMMON_URI = u'http://md.incommon.org/InCommon/InCommon-metadata.xml'

    def __init__(self):
        self.inIncommon = False
        self.inWhitelist = False
        self.inInclude = False
        self.includedEntities = set()
        self.content = ''

    def startElement(self, name, attrs):
        if (name.endswith(ShibbolethHandler.METADATA_PROVIDER)
            and ShibbolethHandler.ATTR_URI in attrs.getNames()
            and (attrs.getValue(ShibbolethHandler.ATTR_URI)
                 == ShibbolethHandler.INCOMMON_URI)):
            self.inIncommon = True
        elif (name.endswith(ShibbolethHandler.METADATA_FILTER)
                and ShibbolethHandler.ATTR_TYPE in attrs.getNames()
                and (attrs.getValue(ShibbolethHandler.ATTR_TYPE)
                         == ShibbolethHandler.VALUE_WHITELIST)):
            self.inWhitelist = True
        elif self.inWhitelist and name.endswith(ShibbolethHandler.INCLUDE):
            self.inInclude = True
            self.content = ''

    def endElement(self, name):
        if self.inIncommon and name.endswith(ShibbolethHandler.METADATA_PROVIDER):
            self.inIncommon = False
        elif self.inWhitelist and name.endswith(ShibbolethHandler.METADATA_FILTER):
            self.inWhitelist = False
        elif self.inWhitelist and name.endswith(ShibbolethHandler.INCLUDE):
            if self.inIncommon:
                self.includedEntities.add(self.content)
            self.inInclude = False

    def characters(self, content):
        self.content = self.content + content


def sendReport(from_addr, to_addrs, subject, body):
    """Send the report about adjusting the Shibboleth configuration.

    """
    if isinstance(to_addrs, basestring):
        to_addrs = [to_addrs]
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ", ".join(to_addrs)
    # print msg.as_string()
    s = smtplib.SMTP('localhost')
    s.sendmail(from_addr, to_addrs, msg.as_string())
    s.quit()

def createReport(actual, desired):
    """Compares the sets actual and desired and reports how actual needs
    to be adjusted to conform to desired. The report text is suitable for
    emailing to an admin who can make the adjustments.
    """
    addList = sorted(desired - actual)
    removeList = sorted(actual - desired)
    report = ''
    if addList:
        report = report + 'Add these:\n'
        for add in addList:
            report = report + '\t%s\n' % (add)
        report = report + '\n'
    if removeList:
        report = report + 'Remove these:\n'
        for remove in removeList:
            report = report + '\t%s\n' % (remove)
        report = report + '\n'
    return report


if __name__ == '__main__':
    icHandler = InCommonHandler()
    errorHandler = RaiseErrorHandler()
    xml.sax.parse(sys.argv[1], icHandler, errorHandler)
    shibHandler = ShibbolethHandler()
    xml.sax.parse(sys.argv[2], shibHandler, errorHandler)
    actualEntities = shibHandler.includedEntities
    desiredEntities = icHandler.includeEntities
    report = createReport(actualEntities, desiredEntities)
    # print report
    if report:
        sendReport('tmitchel@bbn.com', 'tmitchel@bbn.com',
                   'InCommon IdP report', report)
    else:
        sendReport('tmitchel@bbn.com', 'tmitchel@bbn.com',
                   'InCommon IdP report', 'Nothing to update')


# xml.sax.parse('InCommon-metadata-preview.xml', handler)
