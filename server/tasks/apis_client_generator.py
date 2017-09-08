from tasks._check_output import check_output

class ApisClientGenerator(object):

    def __init__(self, filepath):
        self._filepath = filepath
        self._ready = False

    def setup(self):
        if self._ready:
            return
        check_output(['virtualenv', 'venv'], cwd=self._filepath)
        check_output(
            ['venv/bin/pip', 'install', 'google-apis-client-generator==1.4.3'],
            cwd=self._filepath)
        self._ready = True

    def generate_php_client(self, discovery_document_filename, dest_filepath):
        self.setup()
        args = ['venv/bin/generate_library',
                '--input={}'.format(discovery_document_filename),
                '--language=php',
                '--language_variant=1.2.0',
                '--output_dir={}'.format(dest_filepath)]
        check_output(args, cwd=self._filepath)
