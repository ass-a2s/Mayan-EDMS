import json
import logging

from django.core.files import File
from django.db import models, transaction
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from django_celery_beat.models import PeriodicTask, IntervalSchedule
from model_utils.managers import InheritanceManager

from mayan.apps.common.mixins import BackendModelMixin
from mayan.apps.converter.layers import layer_saved_transformations
from mayan.apps.documents.models import DocumentType
from mayan.apps.documents.tasks import task_document_upload
from mayan.apps.storage.compressed_files import Archive
from mayan.apps.storage.exceptions import NoMIMETypeMatch
from mayan.apps.storage.models import SharedUploadedFile

## Remove DEFAULT_INTERVAL import
DEFAULT_INTERVAL = 200
from ..classes import SourceBackendNull
from ..managers import SourceManager
from ..wizards import WizardStep

logger = logging.getLogger(name=__name__)



#TODO: move this to ../models.py
class Source(BackendModelMixin, models.Model):
    _backend_model_null_backend = SourceBackendNull

    label = models.CharField(
        db_index=True, help_text=_('A short text to describe this source.'),
        max_length=128, unique=True, verbose_name=_('Label')
    )
    enabled = models.BooleanField(default=True, verbose_name=_('Enabled'))

    objects = SourceManager()

    class Meta:
        ordering = ('label',)
        verbose_name = _('Source')
        verbose_name_plural = _('Sources')

    @staticmethod
    def callback_post_task_document_upload(
        document_file, query_string, source_id, user=None
    ):
        source = Source.objects.get(pk=source_id)

        if user:
            document_file.document.add_as_recent_document_for_user(user=user)

        layer_saved_transformations.copy_transformations(
            source=source, targets=document_file.pages.all()
        )
        WizardStep.post_upload_process(
            document=document_file.document, query_string=query_string
        )

        #TODO: call source backend callback

    def __str__(self):
        return '%s' % self.label

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            #self.get_backend_instance().delete()
            super().delete(*args, **kwargs)

    def fullname(self):
        #return ' '.join([self.class_fullname(), '"%s"' % self.label])
        return '{} {}'.format(self.get_backend_label(), self.label)

    def handle_file_object_upload(
        self, document_type, file_object, description=None, expand=False,
        label=None, language=None, query_string=None, user=None
    ):
        """
        Handle an upload request from a file object which may be an individual
        document or a compressed file containing multiple documents.
        """
        #documents = []
        #if not document_type:
        #    document_type = DocumentType.objects.get(
        #        pk=self.get_backend_data()['document_type_id']
        #    )

        #kwargs = {
        #    'description': description, 'document_type': document_type,
        #    'label': label, 'language': language, 'user': user
        #}

        query_string = query_string or {}

        if expand:
            try:
                compressed_file = Archive.open(file_object=file_object)
                for compressed_file_member in compressed_file.members():
                    with compressed_file.open_member(filename=compressed_file_member) as compressed_file_member_file_object:
                        # Recursive call to expand nested compressed files
                        # expand=True literal for recursive nested files.
                        # Might cause problem with office files inside a
                        # compressed file.
                        self.handle_file_object_upload(
                            document_type=document_type,
                            description=description,
                            expand=False,
                            file_object=compressed_file_member_file_object,
                            label=force_text(s=compressed_file_member),
                            language=language,
                            query_string=query_string,
                            user=user
                        )

                # Avoid executing the expand=False code path.
                return
            except NoMIMETypeMatch:
                logger.debug(msg='No expanding; Exception: NoMIMETypeMatch')
                # Fallthrough to same code path as expand=False to avoid
                # duplicating code.

        shared_uploaded_file = SharedUploadedFile.objects.create(
            file=File(file_object)
        )

        if user:
            user_id = user.pk
        else:
            user_id = None

        task_document_upload.apply_async(
            kwargs={
                'document_type_id': document_type.pk,
                'shared_uploaded_file_id': shared_uploaded_file.pk,
                'description': description,
                'label': label,
                'language': language,
                'query_string': query_string,
                'user_id': user_id,
                'callback_dotted_path': 'mayan.apps.sources.models.base.Source',
                'callback_function': 'callback_post_task_document_upload',
                'callback_kwargs': {
                    'source_id': self.pk,
                }
            }
        )

            #def task_document_upload(
            #    document_type_id, shared_uploaded_file_id, description=None, label=None,
            #    language=None, querystring=None, user=None, callback=None
            #):

        # Return a list of newly created documents. Used by the email source
        # to assign the from and subject metadata values.
        #return documents

    def save(self, *args, **kwargs):
        with transaction.atomic():
            #self.get_backend_instance().save()
            super().save(*args, **kwargs)


class OutOfProcessSource(Source):
    is_interactive = False

    objects = models.Manager()

    class Meta:
        verbose_name = _('Out of process')
        verbose_name_plural = _('Out of process')


class IntervalBaseModel(OutOfProcessSource):
    interval = models.PositiveIntegerField(
        default=DEFAULT_INTERVAL,
        help_text=_('Interval in seconds between checks for new documents.'),
        verbose_name=_('Interval')
    )
    document_type = models.ForeignKey(
        help_text=_(
            'Assign a document type to documents uploaded from this source.'
        ), on_delete=models.CASCADE, to=DocumentType,
        related_name='interval_sources', verbose_name=_('Document type')
    )
    #uncompress = models.CharField(
    #    choices=SOURCE_UNCOMPRESS_CHOICES,
    #    help_text=_('Whether to expand or not, compressed archives.'),
    #    max_length=1, verbose_name=_('Uncompress')
    #)

    objects = models.Manager()

    class Meta:
        verbose_name = _('Interval source')
        verbose_name_plural = _('Interval sources')

