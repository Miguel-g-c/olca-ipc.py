"""
This is a script for generating the initial model types from the
olca-schema yaml files. To run this script you need to have PyYAML
installed, e.g.:

    pip install pyyaml

You also have to configure the YAML_DIR in this script to point to
the directory where the YAML files are located: 
    # clone the olca-schema repository to some folder
    cd <folder>
    git clone https://github.com/GreenDelta/olca-schema.git
    # <folder>/olca-schema/yaml is the path for the YAML_DIR

After this you can run this script. It will print the generated classes and
enumerations to the console:

    python genmodel.py > [.. path to generated file].py

"""

from os import path

import model


YAML_DIR = path.abspath(path.dirname(__file__)) + '/../../olca-schema/yaml'


def to_snake_case(identifier: str) -> str:
    s = ''
    for char in identifier:
        if char.isupper():
            s += '_'
            s += char.lower()
        else:
            s += char
    return s


def py_type(model_type: str) -> str:
    if model_type == 'string':
        return 'str'
    if model_type == 'double':
        return 'float'
    if model_type == 'boolean':
        return 'bool'
    if model_type == 'integer':
        return 'int'
    if model_type == 'dateTime':
        return 'str'
    if model_type == 'date':
        return 'str'
    if model_type.startswith('Ref['):
        return 'Ref'
    return model_type


def print_class(c: model.ClassType, m: model.Model):
    parent = c.super_class if c.super_class is not None else 'object'
    t = '\nclass %s(%s):\n\n' % (c.name, py_type(parent))
    t += '    def __init__(self):\n'
    if len(c.properties) == 0:
        t += '        self.id = None  # type: str\n'
    else:
        t += '        super(%s, self).__init__()\n' % c.name
    for prop in c.properties:
        attr = to_snake_case(prop.name)
        ptype = py_type(prop.field_type)
        t += '        self.%s = None  # type: %s\n' % (attr, ptype)
    print(t)
    print_to_json(c, m)
    print_from_json(c, m)


def print_to_json(c: model.ClassType, m: model.Model):
    t = '    def to_json(self) -> dict:\n'
    off = '        '
    if len(c.properties) == 0:
        t += off + "json = {'@type': type(self).__name__}\n"
        t += off + 'if self.id is not None:\n'
        t += off + "    json['@id'] = self.id\n"
        t += off + 'return json\n'
    else:
        t += off + 'json = super(%s, self).to_json()  # type: dict\n' % c.name
        for prop in c.properties:
            attr = to_snake_case(prop.name)
            t += off + 'if self.%s is not None:\n' % attr
            is_primitive = prop.field_type[0].islower()
            is_enum = m.find_enum(prop.field_type) is not None
            is_list = prop.field_type.startswith('List[')
            if is_primitive:
                t += off + "    json['%s'] = self.%s\n" % (prop.name, attr)
            elif is_enum:
                t += off + \
                    "    json['%s'] = self.%s.value\n" % (prop.name, attr)
            elif is_list:
                t += off + "    json['%s'] = []\n" % prop.name
                t += off + "    for e in self.%s:\n" % attr
                list_type = py_type(list_elem_type(prop.field_type))
                if list_type[0].islower():
                    t += off + off + "json['%s'].append(e)\n" % prop.name
                else:
                    t += off + off + \
                        "json['%s'].append(e.to_json())\n" % prop.name
            else:
                t += off + \
                    "    json['%s'] = self.%s.to_json()\n" % (prop.name, attr)
        t += off + 'return json\n'
    print(t)


def print_from_json(c: model.ClassType, m: model.Model):
    t = '    def from_json(self, json: dict):\n'
    off = '        '
    if len(c.properties) == 0:
        t += off + "self.id = json.get('@id')\n"
    else:
        t += off + 'super(%s, self).from_json(json)\n' % c.name
        for prop in c.properties:
            attr = to_snake_case(prop.name)
            is_primitive = prop.field_type[0].islower()
            is_enum = m.find_enum(prop.field_type) is not None
            is_list = prop.field_type.startswith('List[')
            t += off + "val = json.get('%s')\n" % prop.name
            t += off + "if val is not None:\n"
            if is_primitive:
                t += off + "    self.%s = val\n" % attr
            elif is_enum:
                t += off + \
                    "    self.%s = %s(val)\n" % (attr, prop.field_type)
            elif is_list:
                t += off + "    self.%s = []\n" % attr
                t += off + "    for d in val:\n"
                t += off + off + 'e = %s()\n' % list_elem_type(py_type(prop.field_type))
                t += off + off + 'e.from_json(d)\n'
                t += off + off + 'self.%s.append(e)\n' % attr
            else:
                t += off + "    self.%s = %s()\n" % (attr, py_type(prop.field_type))
                t += off + "    self.%s.from_json(val)\n" % attr
    print(t)


def list_elem_type(list_type: str) -> str:
    return list_type[5:(len(list_type) - 1)]


def print_enum(e: model.EnumType):
    t = 'class %s(Enum):\n' % e.name
    for item in e.items:
        t += "    %s = '%s'\n" % (item.name, item.name)
    t += '\n'
    print(t)


if __name__ == '__main__':
    print('# This module contains a Python API of the JSON-LD based')
    print('# openLCA data exchange model.package schema.')
    print('# For more information see '
          'http://greendelta.github.io/olca-schema/\n')
    print('from enum import Enum')
    print('from typing import List\n')

    m = model.Model.load_yaml(YAML_DIR)  # type: model.Model
    for enum in m.enums:
        print_enum(enum)
    for clazz in m.classes:
        print_class(clazz, m)
