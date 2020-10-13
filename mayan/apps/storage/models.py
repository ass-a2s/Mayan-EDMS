import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from .classes import DefinedStorageLazy
from .literals import (
    STORAGE_NAME_DOWNLOAD_FILE, STORAGE_NAME_SHARED_UPLOADED_FILE
)
from .managers import DownloadFileManager, SharedUploadedFileManager


def upload_to(instance, filename):
    return 'shared-file-{}'.format(uuid.uuid4().hex)


def download_file_upload_to(instance, filename):
    return 'download-file-{}'.format(uuid.uuid4().hex)


class DownloadFile(models.Model):
    """
    Keep a database link to a stored file. Used for generates files meant
    to be downloaded at a later time.
    """
    file = models.FileField(
        storage=DefinedStorageLazy(
            name=STORAGE_NAME_DOWNLOAD_FILE
        ), upload_to=download_file_upload_to, verbose_name=_('File')
    )
    filename = models.CharField(max_length=255, verbose_name=_('Filename'))
    datetime = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date time')
    )
    content_type = models.ForeignKey(
        blank=True, null=True, on_delete=models.CASCADE, to=ContentType
    )
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey(
        ct_field='content_type', fk_field='object_id'
    )

    objects = DownloadFileManager()

    class Meta:
        verbose_name = _('Download file')
        verbose_name_plural = _('Download files')

    def __str__(self):
        return str(self.content_object) or self.filename

    def delete(self, *args, **kwargs):
        self.file.storage.delete(name=self.file.name)
        return super().delete(*args, **kwargs)

    def open(self, mode=None):
        return self.file.storage.open(
            mode=mode or self.file.file.mode, name=self.file.name
        )

    def save(self, *args, **kwargs):
        self.filename = force_text(self.file)
        super().save(*args, **kwargs)


class SharedUploadedFile(models.Model):
    """
    Keep a database link to a stored file. Used to share files between code
    that runs out of process.
    """
    file = models.FileField(
        storage=DefinedStorageLazy(
            name=STORAGE_NAME_SHARED_UPLOADED_FILE
        ), upload_to=upload_to, verbose_name=_('File')
    )
    filename = models.CharField(max_length=255, verbose_name=_('Filename'))
    datetime = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date time')
    )

    objects = SharedUploadedFileManager()

    class Meta:
        verbose_name = _('Shared uploaded file')
        verbose_name_plural = _('Shared uploaded files')

    def __str__(self):
        return self.filename

    def delete(self, *args, **kwargs):
        self.file.storage.delete(name=self.file.name)
        return super().delete(*args, **kwargs)

    def open(self, mode=None):
        return self.file.storage.open(
            mode=mode or self.file.file.mode, name=self.file.name
        )

    def save(self, *args, **kwargs):
        self.filename = force_text(self.file)
        super().save(*args, **kwargs)
