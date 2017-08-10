import xml.etree.cElementTree as ET
import re
from collections import defaultdict
import numpy as np
from tabulate import tabulate

xmlFileName = "san-francisco-sample.osm"
xmlOutFileName = "san-francisco-sample-modified.osm"


# Auditing City Names : 'addr: city' - if city_name contains numbers remove it
# Fix capitalization, suffix and other inconsistencies
def fixTagCityAddressValue(tagElem):
    oldCityVal = tagElem.attrib['v']
    digitRegexRes = re.compile('\d+').search(oldCityVal)
    caRegexRes = re.compile(',? CA$', re.IGNORECASE).search(oldCityVal)

    if digitRegexRes:
        # print "Drop " + oldCityVal + " since it is a number"
        return None, True
    elif caRegexRes:
        newCityVal = re.sub(caRegexRes.group(), '', oldCityVal)
        tagElem.set('v', newCityVal)
        # print "Change " + oldCityVal + " to " + newCityVal
        return tagElem, True
    else:
        return None, False


# Auditing Country Names : 'addr:country'
# Abbreviate when required and handle misspelled abbreviations
def fixTagCountryAddressValue(tagElem):
    oldCountryVal = tagElem.attrib['v']
    usRegexRes = re.compile('^US$', re.IGNORECASE).search(oldCountryVal)

    if not usRegexRes:
        newCountryVal = re.sub(oldCountryVal, 'US', oldCountryVal)
        tagElem.set('v', newCountryVal)
        # print "Change " + oldCountryVal + " to " + newCountryVal
        return tagElem, True
    else:
        return None, False


# Auditing Post Codes: 'addr:postcode' - Standardize 5 digit Zip code.
# Remove State prefix if found.
def fixTagPostCodeValue(tagElem):
    oldPostCodeVal = tagElem.attrib['v']
    # if code doesn't start with 9, drop
    startRegexRes = re.compile('^9').search(oldPostCodeVal)
    # if code starts with CA, drop the CA portion
    caRgxRes = re.compile('^\s*CA[,: ]*', re.IGNORECASE).search(oldPostCodeVal)

    if caRgxRes:
        newPostCodeVal = re.sub(caRgxRes.group(), '', oldPostCodeVal)
        # print "Change CA vals:'" + oldPostCodeVal + "' to " + newPostCodeVal
        return tagElem, True
    elif not startRegexRes:
        # print "Drop '" + oldPostCodeVal + "' since code is invalid"
        return None, True
    elif len(oldPostCodeVal) > 5:
        newPostCodeVal = oldPostCodeVal[:5]
        tagElem.set('v', newPostCodeVal)
        # print "Change '" + oldPostCodeVal + "' to " + newPostCodeVal
        return tagElem, True
    else:
        return None, False


# Auditing Street Names: 'addr:street' - handle street abbreviations
def fixTagStreetAddressValue(tagElem):
    mapping = {"Ave": "Avenue", "Ave.": "Avenue", "Blvd": "Boulevard",
               "Hwy": "Highway", "Dr": "Drive", "Dr.": "Drive",
               "Wy": "Way", "Rd": "Road", "Rd.": "Road", "St": "Street",
               "St.": "Street", "Ct.": "Court", "Ct": "Court"}
    oldStreetVal = tagElem.attrib['v']
    streetRegexRes = re.compile(r'\S+$', re.IGNORECASE).search(oldStreetVal)

    if streetRegexRes and mapping.get(streetRegexRes.group()):
        newStreetVal = re.sub(streetRegexRes.group(),
                              mapping[streetRegexRes.group()],
                              oldStreetVal)
        tagElem.set('v', newStreetVal)
        # print "Replace " + oldStreetVal + " to " + newStreetVal
        return tagElem, True
    else:
        return None, False


# Auditing State Name: 'addr:state' - Standardize state as 'CA'
def fixTagStateAddressValue(tagElem):
    oldStateVal = tagElem.attrib['v']
    caRegexRes = re.compile('^CA$').search(oldStateVal)

    if not caRegexRes:
        newStateVal = re.sub(oldStateVal, 'CA', oldStateVal)
        tagElem.set('v', newStateVal)
        # print "Change " + oldStateVal + " to " + newStateVal
        return tagElem, True
    else:
        return None, False


# Process all the root-tags of interest across the entire XML
def processTags(fileName, tagList=["node", "way"], writeToFile=False):
    attribList = ["addr:country", "addr:city", "addr:postcode",
                  "addr:street", "addr:state"]
    cityCnt, countryCnt, postCodeCnt, streetCnt, stateCnt = 0, 0, 0, 0, 0
    xmlContext = ET.iterparse(fileName, events=("start",))
    for _, elem in xmlContext:
        if elem.tag in tagList:
            for tagElem in elem.iter("tag"):
                changedTagElem = None
                isChanged = False
                if tagElem.attrib['k'] not in attribList:
                    continue
                if tagElem.attrib['k'] == "addr:country":
                    countryCnt += 1
                    changedTagElem, isChanged = fixTagCountryAddressValue(tagElem)
                elif tagElem.attrib['k'] == "addr:city":
                    cityCnt += 1
                    changedTagElem, isChanged = fixTagCityAddressValue(tagElem)
                elif tagElem.attrib['k'] == "addr:postcode":
                    postCodeCnt += 1
                    changedTagElem, isChanged = fixTagPostCodeValue(tagElem)
                elif tagElem.attrib['k'] == "addr:street":
                    streetCnt += 1
                    changedTagElem, isChanged = fixTagStreetAddressValue(tagElem)
                elif tagElem.attrib['k'] == "addr:state":
                    stateCnt += 1
                    changedTagElem, isChanged = fixTagStateAddressValue(tagElem)
                # Propagate the change onto the XML tree
                if isChanged and writeToFile:
                    if changedTagElem:
                        elem.replace(tagElem, changedTagElem)
                    else:
                        elem.remove(tagElem)
    totalModified = streetCnt + cityCnt + stateCnt + countryCnt + postCodeCnt
    print "#Tags fixed with this script:"
    result = np.column_stack((attribList, [streetCnt, cityCnt, stateCnt,
                                           countryCnt, postCodeCnt]))
    print tabulate(result)
    print "Total      " + str(totalModified)
    if totalModified and writeToFile:
        print "Generating XML " + xmlOutFileName
        ET.ElementTree(xmlContext.root).write(xmlOutFileName)


processTags(xmlFileName, writeToFile=True)
