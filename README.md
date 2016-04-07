# eduGAIN

A small program to compare the
[InCommon metadata](http://md.incommon.org/InCommon/InCommon-metadata.xml)
to a local `shibboleth2.xml`
file and issue a report of identity providers to be added to or removed from
`shibboleth2.xml` so that only InCommon identity providers are allowed by the
local Shibboleth SP.

This effectively filters out the eduGAIN identity providers while still loading
the full InCommon metadata file.
