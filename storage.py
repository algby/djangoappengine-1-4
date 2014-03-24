import mimetypes
import os
import re

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.files.uploadedfile import UploadedFile
from django.core.files.uploadhandler import FileUploadHandler, \
    StopFutureHandlers
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.http.multipartparser import ChunkIter, Parser, LazyStream, FILE
from django.utils.encoding import smart_str, force_unicode

from google.appengine.api import files
from google.appengine.api.images import get_serving_url, NotImageError
from google.appengine.ext.blobstore import BlobInfo, BlobKey, delete, \
    create_upload_url, BLOB_KEY_HEADER, BLOB_RANGE_HEADER, BlobReader


def prepare_upload(request, url, **kwargs):
    return create_upload_url(url), {}


def serve_file(request, file, save_as, content_type, **kwargs):
    if isinstance(file, BlobKey):
        blobkey = file
    elif hasattr(file, 'file') and hasattr(file.file, 'blobstore_info'):
        blobkey = file.file.blobstore_info.key()
    elif hasattr(file, 'blobstore_info'):
        blobkey = file.blobstore_info.key()
    else:
        raise ValueError("The provided file can't be served via the "
                         "Google App Engine Blobstore.")
    response = HttpResponse(content_type=content_type)
    response[BLOB_KEY_HEADER] = str(blobkey)
    response['Accept-Ranges'] = 'bytes'
    http_range = request.META.get('HTTP_RANGE')
    if http_range is not None:
        response[BLOB_RANGE_HEADER] = http_range
    if save_as:
        response['Content-Disposition'] = smart_str(
            u'attachment; filename="%s"' % save_as)

    info = BlobInfo.get(blobkey)
    if info.size is not None:
        response['Content-Length'] = info.size
    return response


class BlobstoreStorage(Storage):
    """Google App Engine Blobstore storage backend."""

    def _open(self, name, mode='rb'):
        return BlobstoreFile(name, mode, self)

    def _save(self, name, content):
        name = name.replace('\\', '/')
        if hasattr(content, 'file') and \
           hasattr(content.file, 'blobstore_info'):
            data = content.file.blobstore_info
        elif hasattr(content, 'blobstore_info'):
            data = content.blobstore_info
        elif isinstance(content, File):
            guessed_type = mimetypes.guess_type(name)[0]
            file_name = files.blobstore.create(mime_type=guessed_type or 'application/octet-stream',
                                               _blobinfo_uploaded_filename=name)

            with files.open(file_name, 'a') as f:
                for chunk in content.chunks():
                    f.write(chunk)

            files.finalize(file_name)

            data = files.blobstore.get_blob_key(file_name)
        else:
            raise ValueError("The App Engine storage backend only supports "
                             "BlobstoreFile instances or File instances.")

        if isinstance(data, (BlobInfo, BlobKey)):
            # We change the file name to the BlobKey's str() value.
            if isinstance(data, BlobInfo):
                data = data.key()
            return '%s/%s' % (data, name.lstrip('/'))
        else:
            raise ValueError("The App Engine Blobstore only supports "
                             "BlobInfo values. Data can't be uploaded "
                             "directly. You have to use the file upload "
                             "handler.")

    def delete(self, name):
        delete(self._get_key(name))

    def exists(self, name):
        return self._get_blobinfo(name) is not None

    def size(self, name):
        return self._get_blobinfo(name).size

    def url(self, name):
        try:
            #return a protocol-less URL, because django can't/won't pass
            #down an argument saying whether it should be secure or not
            url = get_serving_url(self._get_blobinfo(name))
            return re.sub("http://", "//", url)
        except NotImageError:
            return None

    def created_time(self, name):
        return self._get_blobinfo(name).creation

    def get_valid_name(self, name):
        return force_unicode(name).strip().replace('\\', '/')

    def get_available_name(self, name):
        return name.replace('\\', '/')

    def _get_key(self, name):
        return BlobKey(name.split('/', 1)[0])

    def _get_blobinfo(self, name):
        return BlobInfo.get(self._get_key(name))


class BlobstoreFile(File):

    def __init__(self, name, mode, storage):
        self.name = name
        self._storage = storage
        self._mode = mode
        self.blobstore_info = storage._get_blobinfo(name)

    @property
    def size(self):
        return self.blobstore_info.size

    def write(self, content):
        raise NotImplementedError()

    @property
    def file(self):
        if not hasattr(self, '_file'):
            self._file = BlobReader(self.blobstore_info.key())
        return self._file


class BlobstoreFileUploadHandler(FileUploadHandler):
    """
    File upload handler for the Google App Engine Blobstore.
    """
    def __init__(self, request=None):
        super(BlobstoreFileUploadHandler, self).__init__(request)
        self.blobkey = None

    def new_file(self, field_name, file_name, content_type, content_length, charset=None, content_type_extra=None):
        """
            We can kill a lot of this hackery in Django 1.7 when content_type_extra is actually passed in!
        """

        def _guess_boundary(_data):
            """According to wikipedia, the boundary always ends a message but is followed by, and prefixed by '--'
            so theoretically, this should always return the correct boundary. Unless I'm wrong, in which case it won't."""
            return _data.rsplit("--")[-2]

        wsgi_input = self.request.META['wsgi.input']
        wsgi_input.seek(0) #Rewind
        data = wsgi_input.read()

        parts = data.split(_guess_boundary(data))

        for part in parts:
            match = re.search('blob-key="(?P<blob_key>\S+)"', part)
            blob_key = match.groupdict().get('blob_key') if match else None

            if not blob_key:
                continue

            #OK, we have a blob key, but is it the one for the field?
            match = re.search('name="(?P<field_name>\S+)"', part)
            name = match.groupdict().get('field_name') if match else None
            if name != field_name:
                #Nope, not for this field
                continue

            self.blobkey = blob_key

        if self.blobkey:
            self.blobkey = BlobKey(self.blobkey)
            raise StopFutureHandlers()
        else:
            return super(BlobstoreFileUploadHandler, self).new_file(field_name, file_name, content_type, content_length, charset)

    def receive_data_chunk(self, raw_data, start):
        """
        Add the data to the StringIO file.
        """
        if not self.blobkey:
            return raw_data

    def file_complete(self, file_size):
        """
        Return a file object if we're activated.
        """
        if not self.blobkey:
            return

        return BlobstoreUploadedFile(
            blobinfo=BlobInfo(self.blobkey),
            charset=self.charset)


class BlobstoreUploadedFile(UploadedFile):
    """
    A file uploaded into memory (i.e. stream-to-memory).
    """

    def __init__(self, blobinfo, charset):
        super(BlobstoreUploadedFile, self).__init__(
            BlobReader(blobinfo.key()), blobinfo.filename,
            blobinfo.content_type, blobinfo.size, charset)
        self.blobstore_info = blobinfo

    def open(self, mode=None):
        pass

    def chunks(self, chunk_size=1024 * 128):
        self.file.seek(0)
        while True:
            content = self.read(chunk_size)
            if not content:
                break
            yield content

    def multiple_chunks(self, chunk_size=1024 * 128):
        return True
