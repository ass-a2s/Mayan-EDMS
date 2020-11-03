import json
import logging

from django.db import models, transaction
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from django_celery_beat.models import PeriodicTask, IntervalSchedule
from model_utils.managers import InheritanceManager

from mayan.apps.common.mixins import BackendModelMixin
from mayan.apps.converter.layers import layer_saved_transformations
from mayan.apps.documents.models import DocumentType
from mayan.apps.storage.compressed_files import Archive
from mayan.apps.storage.exceptions import NoMIMETypeMatch

## Remove DEFAULT_INTERVAL import
from ..literals import DEFAULT_INTERVAL, SOURCE_UNCOMPRESS_CHOICES
from ..wizards import WizardStep

logger = logging.getLogger(name=__name__)


#TODO: Move to managers.py
class SourceManager(models.Manager):
    def interactive(self):
        interactive_sources_ids = []
        for source in self.all():
            if getattr(source.get_backend(), 'is_interactive', False):
                interactive_sources_ids.append(source.pk)

        return self.filter(id__in=interactive_sources_ids)


class Source(BackendModelMixin, models.Model):
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

    def __str__(self):
        return '%s' % self.label

    def clean_up_upload_file(self, upload_file_object):
        pass
        # TODO: Should raise NotImplementedError?

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            #self.get_backend_instance().delete()
            super().delete(*args, **kwargs)

    def fullname(self):
        #return ' '.join([self.class_fullname(), '"%s"' % self.label])
        return '{} {}'.format(self.get_backend_label(), self.label)

    #def get_upload_file_object(self, form_data):
    #    pass
    #    # TODO: Should raise NotImplementedError?

    def handle_upload(
        self, file_object, description=None, document_type=None, expand=False,
        label=None, language=None, user=None
    ):
        """
        Handle an upload request from a file object which may be an individual
        document or a compressed file containing multiple documents.
        """
        documents = []
        if not document_type:
            document_type = DocumentType.objects.get(
                pk=self.get_backend_data()['document_type_id']
            )

        kwargs = {
            'description': description, 'document_type': document_type,
            'label': label, 'language': language, 'user': user
        }

        if expand:
            try:
                compressed_file = Archive.open(file_object=file_object)
                for compressed_file_child in compressed_file.members():
                    with compressed_file.open_member(filename=compressed_file_child) as file_object:
                        kwargs.update(
                            {'label': force_text(s=compressed_file_child)}
                        )
                        documents.append(
                            self.upload_document(
                                file_object=file_object, **kwargs
                            )
                        )
            except NoMIMETypeMatch:
                logger.debug(msg='Exception: NoMIMETypeMatch')
                documents.append(
                    self.upload_document(file_object=file_object, **kwargs)
                )
        else:
            documents.append(
                self.upload_document(file_object=file_object, **kwargs)
            )

        # Return a list of newly created documents. Used by the email source
        # to assign the from and subject metadata values.
        return documents

    def save(self, *args, **kwargs):
        with transaction.atomic():
            #self.get_backend_instance().save()
            super().save(*args, **kwargs)

    def upload_document(
        self, file_object, document_type, description=None, label=None,
        language=None, querystring=None, user=None
    ):
        """
        Upload an individual document
        """
        document = None
        try:

            document, document_file = document_type.new_document(
                file_object=file_object, label=label,
                description=description, language=language,
                _user=user
            )
        except Exception as exception:
            logger.critical(
                'Unexpected exception while trying to create new document '
                '"%s" from source "%s"; %s',
                label or file_object.name, self, exception
            )
            if document:
                document.delete(to_trash=False)
            raise
        else:
            if user:
                document.add_as_recent_document_for_user(user=user)

            layer_saved_transformations.copy_transformations(
                source=self, targets=document_file.pages.all()
            )
            WizardStep.post_upload_process(
                document=document, querystring=querystring
            )
            return document


class InteractiveSource(Source):
    objects = InheritanceManager()

    class Meta:
        verbose_name = _('Interactive source')
        verbose_name_plural = _('Interactive sources')


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
    uncompress = models.CharField(
        choices=SOURCE_UNCOMPRESS_CHOICES,
        help_text=_('Whether to expand or not, compressed archives.'),
        max_length=1, verbose_name=_('Uncompress')
    )

    objects = models.Manager()

    class Meta:
        verbose_name = _('Interval source')
        verbose_name_plural = _('Interval sources')

