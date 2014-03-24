from cStringIO import StringIO
from django.core.files.uploadhandler import StopFutureHandlers
from django.test import TestCase, RequestFactory

from ..storage import BlobstoreFileUploadHandler


class BlobstoreFileUploadHandlerTest(TestCase):
    boundary = "===============7417945581544019063=="

    def setUp(self):
        self.request = RequestFactory().get('/')
        self.request.META = {'wsgi.input': self._create_wsgi_input()}
        self.uploader = BlobstoreFileUploadHandler(self.request)

    def _create_wsgi_input(self):
        return StringIO('--===============7417945581544019063==\r\nContent-Type:'
                        ' text/plain\r\nContent-Disposition: form-data;'
                        ' name="field-nationality"\r\n\r\nAS\r\n'
                        '--===============7417945581544019063==\r\nContent-Type:'
                        ' message/external-body; blob-key="PLOF0qOie14jzHWJXEa9HA==";'
                        ' access-type="X-AppEngine-BlobKey"\r\nContent-Disposition:'
                        ' form-data; name="field-file";'
                        ' filename="Scan.tiff"\r\n\r\nContent-Type: image/tiff'
                        '\r\nContent-Length: 19837164\r\nContent-MD5:'
                        ' YjI1M2Q5NjM5YzdlMzUxYjMyMjA0ZTIxZjAyNzdiM2Q=\r\ncontent-disposition:'
                        ' form-data; name="field-file";'
                        ' filename="Scan.tiff"\r\nX-AppEngine-Upload-Creation: 2014-03-07'
                        ' 14:48:03.246607\r\n\r\n\r\n'
                        '--===============7417945581544019063==\r\nContent-Type:'
                        ' text/plain\r\nContent-Disposition: form-data;'
                        ' name="field-number"\r\n\r\n6\r\n'
                        '--===============7417945581544019063==\r\nContent-Type:'
                        ' text/plain\r\nContent-Disposition: form-data;'
                        ' name="field-salutation"\r\n\r\nmrs\r\n'
                        '--===============7417945581544019063==--')

    def test_blob_key_gets_parsed_out(self):
        self.uploader.handle_raw_input(None, None, None,
                                       boundary=self.boundary.encode('ascii'),
                                       encoding='utf-8')

        file_field_name = 'field-file'
        self.assertTrue(file_field_name in self.uploader.content_type_extras.keys())
        self.assertEqual(
            self.uploader.content_type_extras[file_field_name].get('blob-key'),
            "PLOF0qOie14jzHWJXEa9HA=="
        )

    def test_non_existing_files_do_not_get_created(self):
        file_field_name = 'field-file'
        self.uploader.content_type_extras[file_field_name] = {}
        self.uploader.new_file(file_field_name, 'file_name', None, None)
        self.assertFalse(self.uploader.active)
        self.assertIsNone(self.uploader.file_complete(None))

    def test_blob_key_creation(self):
        file_field_name = 'field-file'
        self.uploader.content_type_extras[file_field_name] = {
            'blob-key': "PLOF0qOie14jzHWJXEa9HA=="
        }
        self.assertRaises(
            StopFutureHandlers,
            self.uploader.new_file, file_field_name, 'file_name', None, None
        )
        self.assertTrue(self.uploader.active)
        self.assertIsNotNone(self.uploader.blobkey)
