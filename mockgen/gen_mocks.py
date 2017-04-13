import argparse
import json
import os
import re
import sys


_PROXY_HTML = """<!DOCTYPE html>
<html>
<head>
<title></title>
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<script type="text/javascript">
  window['startup'] = function() {
    googleapis.server.init();
  };
</script>
<script type="text/javascript"
  src="https://apis.google.com/js/googleapis.proxy.js?onload=startup" async
  defer></script>
</head>
<body>
</body>
</html>
"""


class Generator(object):

    _CAST_FUNC = {
        'any': 'dict',
        'array': 'list',
        'boolean': 'bool',
        'integer': 'int',
        'number': 'float',
        'object': 'dict',
        'string': 'str'
    }

    _INSTANCE = {
        'any': 'object',
        'array': 'list',
        'boolean': 'bool',
        'integer': 'int',
        'number': 'float',
        'object': 'dict',
        'string': 'basestring'
    }

    _file = sys.stdout

    def __init__(self, root):
        self._root = root

        schemas = {}
        for schema in root.get('schemas', {}).itervalues():
            id_ = schema['id']
            schemas[id_] = schema
        self._schemas = schemas

    def set_file(self, file_):
        self._file = file_

    def emit(self, method):
        w = self._w

        w('from flask import Flask')
        w('from flask import jsonify')
        w('from flask import request')
        w('')
        w('app = Flask(__name__)')
        w('')

        self._emit_method(method)

        w('')
        w('def error(code, msg):')
        payload = '{"error": {"code": code, "message": msg, "details": []}}'
        w('    return code, {}'.format(payload))
        w('')

        w('if __name__ == "__main__":')
        w('    app.run()')

    def _emit_method(self, method):
        w = self._w

        path = method['path'].strip('/')
        service_path = self._root['servicePath'].strip('/')
        # The full path is actually "{servicePath}/{path}".
        path = '/'.join([service_path, path]).strip('/')

        # Pull all the braced URL variable names out of the path.
        # Note that we ignore the '+' in multi-segment variable names.
        # Variable names are escaped to prevent naming conflicts.
        # ex: '/foo/{bar}/{+baz}' => ['bar_', 'baz_']
        url_vars = [_esc_var(x) for x in re.findall(r'{\+?([^}]+)}', path)]

        # Convert path into a Flask route.
        # ex: "{+foo}" => "<path:foo>"
        path = re.sub(r'{(\+[^}]+)}', '<path:{}>', path)
        # ex: "{foo}" => "<string:foo>"
        path = re.sub('{([^}]+)}', '<string:{}>', path)
        path = path.format(*url_vars)

        http_method = method['httpMethod']
        w('@app.route("/{}", methods=["{}"])'.format(path, http_method))
        method_name = method['id'].replace('.', '_')
        w('def {}({}):'.format(method_name, ', '.join(url_vars)))

        params = method.get('parameters', {})
        param_order = method.get('parameterOrder', {})
        for name in param_order:
            self._emit_param_assert(name, params[name])

        if 'request' in method:
            w('    if not request.data:')
            w('        return error(400, "expected a request body")')
            w('    if not isinstance(request.get_json(), dict):')
            msg = 'expected the request body to be an instance of \\"dict\\"'
            w('        return error(400, "{}")'.format(msg))
        else:
            w('    if request.data:')
            w('        return error(400, "unexpected request body")')

        if 'response' in method:
            ref = method['response']['$ref']
            obj = self._gen_type(self._schemas[ref])
            w('    return jsonify({})'.format(obj))
        else:
            w('    return jsonify({})')

    def _emit_param_assert(self, name, param):
        w = self._w

        # The only way that 'type' is not a property of param is if it contains
        # a reference to another schema. In that case we assume it's an object.
        type_ = param.get('type', 'object')
        cast_func = self._CAST_FUNC[type_]
        instance = self._INSTANCE[type_]

        location = param['location']
        if location == 'query':
            w('    if "{}" not in request.args:'.format(name))
            msg = 'query parameter \\"{}\\" not found'.format(name)
            w('        return error(400, "{}")'.format(msg))
            w('    try:')
            cast_func = self._CAST_FUNC[type_]
            w('        {}(request.args.get("{}"))'.format(cast_func, name))
            w('    except:')
            msg = 'expected \\"{}\\" to be an instance of \\"{}\\"'
            msg = msg.format(name, instance)
            w('        return error(400, "{}")'.format(msg))
        else: # location == 'path'
            # Path params are accessed as variables passed into the function.
            # The variable name is reconstructed here from the param name.
            var = _esc_var(name)
            w('    if not isinstance({}, {}):'.format(var, instance))
            msg = 'expected \\"{}\\" to be an instance of \\"{}\\"'
            msg = msg.format(name, instance)
            w('        return error(400, "{}")'.format(msg))

    def _gen_type(self, schema, visited=None):
        if visited is None:
            visited = {}
        if '$ref' in schema:
            param = self._schemas[schema['$ref']]
            return self._gen_type(param, visited)
        type_ = schema['type']
        if type_ == 'any':
            return {}
        if type_ == 'array':
            return [self._gen_type(schema['items'], visited)]
        if type_ == 'boolean':
            return False
        if type_ == 'integer':
            return 0
        if type_ == 'number':
            return 0
        if type_ == 'object':
            obj = {}
            id_ = schema.get('id')
            if id_ in visited:
                return obj
            # Nested objects don't have IDs.
            if id_:
                visited[id_] = True
            for key, val in schema.get('properties', {}).iteritems():
                obj[key] = self._gen_type(val, visited)
            return obj
        if type_ == 'string':
            return {
                'int32': 0,
                'uint32': 0,
                'double': 0.,
                'float': 0.,
                'date': '1970-01-01',
                'date-time': '1970-01-01T00:00:00-07:00',
                'int64': '0',
                'uint64': '0',
            }.get(schema.get('format'), '')
        raise Exception('unexpected type: {}'.format(type_))

    def _w(self, data):
        self._file.write(data + '\n')


def _esc_var(name):
    # Return an identifier that can't conflict with any
    # built-ins/keywords/other vars.
    return name + '_'


def _parse_methods(root, methods=None):
    if methods is None:
        methods = {}
    for method in root.get('methods', {}).itervalues():
        id_ = method['id']
        methods[id_] = method
    for resource in root.get('resources', {}).itervalues():
        _parse_methods(resource, methods)
    return methods


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--directory', default='mocks')
    args = parser.parse_args()

    root = {}
    with open(args.file) as file_:
        root = json.load(file_)

    methods = _parse_methods(root)
    gen = Generator(root)

    if not os.path.exists(args.directory):
        os.makedirs(args.directory)
    static_dir = os.path.join(args.directory, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    root_copy = root.copy()
    root_copy['rootUrl'] = 'http://localhost:5000/'
    name, version = root['name'], root['version']
    ddoc_path = os.path.join(static_dir, '{}.{}.json'.format(name, version))
    # Write the modified discovery doc to the static directory.
    with open(ddoc_path, 'w') as file_:
        file_.write(json.dumps(root_copy, sort_keys=True, indent=2))
    # Write proxy.html to the static directory.
    # proxy.html is required by the JavaScript client library.
    with open(os.path.join(static_dir, 'proxy.html'), 'w') as file_:
        file_.write(_PROXY_HTML)

    for key, val in methods.iteritems():
        path = os.path.join(args.directory, key + '.mock.py')
        with open(path, 'w') as file_:
            print path
            gen.set_file(file_)
            gen.emit(val)


if __name__ == '__main__':
    main()
