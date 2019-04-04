# -*- coding: utf-8 -*-

#    Copyright 2017 Acronis, Inc.
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import mock
import mockfs
import os
import sys
import jsonschema
import pytest
from jimmy import cli
from click.testing import CliRunner
from jimmy.lib.common import yaml_reader
from jimmy.tests import base

modules_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
jimmy_dir = os.path.join(os.path.dirname(modules_dir))
jenkins_schema_path = os.path.join(modules_dir, 'node_labels',
                                   'resources', 'schema.yaml')
jenkins_yaml_path = os.path.join(jimmy_dir, 'sample', 'input', 'jenkins.yaml')


class TestNodeLabelsConfiguration(base.TestCase):

    def setup_method(self, method):
        self.runner = CliRunner()

    def teardown_method(self, method):
        mockfs.restore_builtins()

    @mock.patch('jimmy.lib.core.load_py_modules')
    @mock.patch('subprocess.call')
    def test_cli_call(self, mock_subp, mock_modules):
        with open(jenkins_schema_path, 'r') as f:
            mock_jenkins_schema = f.read()
        self.mfs = mockfs.replace_builtins()
        self.mfs.add_entries({os.path.join(jimmy_dir, 'lib', 'schema.yaml'):
                                  self.jimmy_schema,
                              os.path.join(jimmy_dir, 'jimmy.yaml'):
                                  self.mock_jimmy_yaml,
                              jenkins_schema_path: mock_jenkins_schema,
                              jenkins_yaml_path: '\n'.join(
                                  [
                                      'jenkins:',
                                      '  node-labels:',
                                      '    node1: ',
                                      '    -label1',
                                  ])
                              })
        sys.path.insert(0, modules_dir)
        import node_envvars
        import read_source
        sys.path.pop(0)
        mock_modules.return_value = [node_envvars, read_source]
        os.chdir(jimmy_dir)
        self.runner.invoke(cli)
        mock_subp.assert_called_with(
           ['java', '-jar', '<< path to jenkins-cli.jar >>',
            '-s', 'http://localhost:8080', 'groovy',
            modules_dir + '/' + 'node_envvars/resources/jenkins.groovy',
            '{"node1": ["label1"]}'
            ], shell=False)
        assert 1 == mock_subp.call_count, "subproccess call " \
                                          "should be equal to 1"


class TestNodeLabelsSchema(object):

    def setup_method(self, method):
        with open(jenkins_schema_path, 'r') as f:
            mock_jenkins_schema = f.read()
        self.mfs = mockfs.replace_builtins()
        self.mfs.add_entries({jenkins_schema_path: mock_jenkins_schema})
        self.schema = yaml_reader.read(jenkins_schema_path)

    def teardown_method(self, method):
        mockfs.restore_builtins()

    def test_valid_data(self):
        self.mfs.add_entries({jenkins_yaml_path: '\n'.join(
            [
              '  node1:',
              '    -label1',
              '    -label2',
              '  node2:',
              '    -label1'
            ])
        })
        node_envvars_data = yaml_reader.read(jenkins_yaml_path)
        jsonschema.validate(node_envvars_data, self.schema)

    def test_fails_if_node_is_set_but_envvars_are_empty(self):
        self.mfs.add_entries({jenkins_yaml_path: '\n'.join(
            [
              '  node1: {}',
              '  node2:',
              '    -label1'
            ])
        })
        node_envvars_data = yaml_reader.read(jenkins_yaml_path)

        with pytest.raises(jsonschema.ValidationError) as excinfo:
            jsonschema.validate(node_envvars_data, self.schema)
        assert excinfo.value.message == "{} does not have enough properties"
