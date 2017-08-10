import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET

import cerberus

import schema


# Converting the cleaned osm file to csv

OSM_PATH = "san-francisco_sample.osm"
# OSM_PATH = "san-francisco-modified.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the field order in all csv files match the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


# Common function to process 'nd' child element in 'way' element
def process_child_nd_element(element, child, nds, position):
    nd = dict.fromkeys(['id', 'node_id', 'position'])  # way-nd
    nd['id'] = element.attrib['id']
    nd['node_id'] = child.attrib['ref']
    nd['position'] = position
    position += 1
    nds.append(nd)
    return position


# Common function to process 'tag' child element in 'node/way' element
def process_child_tag_element(element, child, tags):
    if PROBLEMCHARS.match(child.attrib['k']):
        return
    tag = dict.fromkeys(['type', 'key', 'id', 'value'])
    tag['id'] = element.attrib['id']
    tag['value'] = child.attrib['v']
    if LOWER_COLON.match(child.attrib['k']):
        tag['type'] = child.attrib['k'].split(':', 1)[0]
        tag['key'] = child.attrib['k'].split(':', 1)[1]
    else:
        tag['type'] = 'regular'
        tag['key'] = child.attrib['k']
    tags.append(tag)


def shape_element(element):
    """Clean and shape node or way XML element to Python dict"""
    node_attribs = dict.fromkeys(NODE_FIELDS)
    way_attribs = dict.fromkeys(WAY_FIELDS)
    tags = []  # List of child node (node/way) 'tag' dictionaries
    nds = []  # List of child node (way) 'nd' dictionaries

    if element.tag == 'node':
        for attrib in node_attribs.iterkeys():
            if attrib in element.attrib:
                node_attribs[attrib] = element.attrib[attrib]
            else:  # node element is missing attrib we want, so drop node
                return None
        for child in element:
            if child.tag == 'tag':
                process_child_tag_element(element, child, tags)

    elif element.tag == 'way':
        for attrib in way_attribs.iterkeys():
            if attrib in element.attrib:
                way_attribs[attrib] = element.attrib[attrib]
            else:  # way element is missing attrib we want, so drop way
                return None
        pos = 0
        for child in element:
            if child.tag == 'tag':
                process_child_tag_element(element, child, tags)
            elif child.tag == 'nd':
                pos = process_child_nd_element(element, child, nds, pos)
    if element.tag == 'node':
        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':
        return {'way': way_attribs, 'way_nodes': nds, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        print element
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has following errors:\n{1}"
        error_string = pprint.pformat(errors)
        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
        codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
        codecs.open(WAYS_PATH, 'w') as ways_file, \
        codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
        codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)
