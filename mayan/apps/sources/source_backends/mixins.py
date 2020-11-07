import errno
import fcntl
import json
import logging
import os
from pathlib import Path
import subprocess

from django.apps import apps
from django.db import transaction
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from mayan.apps.appearance.classes import Icon
from mayan.apps.documents.literals import DOCUMENT_FILE_ACTION_PAGES_NEW
from mayan.apps.documents.models.document_models import Document
from mayan.apps.documents.models.document_file_models import DocumentFile
from mayan.apps.documents.models.document_type_models import DocumentType
from mayan.apps.documents.permissions import permission_document_file_new
from mayan.apps.documents.tasks import task_document_file_upload
from mayan.apps.common.serialization import yaml_load
from mayan.apps.common.validators import YAMLValidator
from mayan.apps.storage.models import SharedUploadedFile
from mayan.apps.storage.utils import TemporaryFile

from ..exceptions import SourceException
from ..literals import (
    DEFAULT_INTERVAL, SOURCE_INTERACTIVE_UNCOMPRESS_CHOICES,
    SOURCE_UNCOMPRESS_CHOICE_ALWAYS, SOURCE_UNCOMPRESS_CHOICE_ASK
)
from ..tasks import task_process_document_upload


class SourceBackendMixinPeriodic:
    def _delete_periodic_task(self, pk=None):
        PeriodicTask = apps.get_model(
            app_label='django_celery_beat', model_name='PeriodicTask'
        )

        try:
            periodic_task = PeriodicTask.objects.get(
                name=self._get_periodic_task_name(pk=pk)
            )

            interval_instance = periodic_task.interval

            #TODO:Update to use the a queryset
            if tuple(interval_instance.periodictask_set.values_list('id', flat=True)) == (periodic_task.pk,):
                # Only delete the interval if nobody else is using it
                interval_instance.delete()
            else:
                periodic_task.delete()
        except PeriodicTask.DoesNotExist:
            logger.warning(
                'Tried to delete non existent periodic task "%s"',
                self._get_periodic_task_name(pk)
            )

    def _get_periodic_task_name(self, pk=None):
        return 'check_interval_source-%i' % (pk or self.pk)

    def check(self, test=False):
        try:
            self._check_source(test=test)
        except Exception as exception:
            self.get_model_instance().error_log.create(
                text='{}; {}'.format(
                    exception.__class__.__name__, exception
                )
            )
            raise
        else:
            self.get_model_instance().error_log.all().delete()

    def delete(self, *args, **kwargs):
        pk = self.pk
        with transaction.atomic():
            self._delete_periodic_task(pk=pk)


class SourceBackendInteractiveMixin:
    def process_document_file(self, document, forms, request):
        shared_uploaded_file = self.get_shared_uploaded_file(forms=forms)

        if not request.user.is_anonymous:
            user = request.user
            user_id = request.user.pk
        else:
            user = None
            user_id = None

        DocumentFile.execute_pre_create_hooks(
            kwargs={
                'document': document,
                'shared_uploaded_file': shared_uploaded_file,
                'user': user
            }
        )

        task_document_file_upload.apply_async(
            kwargs={
                'action': int(
                    forms['document_form'].cleaned_data.get('action')
                ),
                'comment': forms['document_form'].cleaned_data.get('comment'),
                'document_id': document.pk,
                'shared_uploaded_file_id': shared_uploaded_file.pk,
                'user_id': user_id
            }
        )

    def process_document(self, document_type, forms, request):
        # For compressed sources only
        if getattr(self, 'can_uncompress', False):
            if self.kwargs['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ASK:
                expand = forms['source_form'].cleaned_data.get('expand')
            else:
                if self.kwargs['uncompress'] == SOURCE_UNCOMPRESS_CHOICE_ALWAYS:
                    expand = True
                else:
                    expand = False
        else:
            expand = False

        shared_uploaded_file = self.get_shared_uploaded_file(forms=forms)

        #source_backend_instance.clean_up_upload_file(
        #    upload_file_object=uploaded_file
        #)

        if not request.user.is_anonymous:
            user = request.user
            user_id = request.user.pk
        else:
            user = None
            user_id = None

        query_string = request.GET.copy()
        query_string.update(request.POST)

        Document.execute_pre_create_hooks(
            kwargs={
                'document_type': document_type,
                'user': user
            }
        )

        DocumentFile.execute_pre_create_hooks(
            kwargs={
                'document_type': document_type,
                'shared_uploaded_file': shared_uploaded_file,
                'user': user
            }
        )

        task_process_document_upload.apply_async(
            kwargs={
                'description': forms['document_form'].cleaned_data.get('description'),
                'document_type_id': document_type.pk,
                'expand': expand,
                'label': forms['document_form'].get_final_label(
                    filename=force_text(shared_uploaded_file)
                ),
                'language': forms['document_form'].cleaned_data.get('language'),
                'query_string': query_string.urlencode(),
                'shared_uploaded_file_id': shared_uploaded_file.pk,
                'source_id': self.model_instance_id,
                'user_id': user_id,
            }
        )


    def save(self):
        IntervalSchedule = apps.get_model(
            app_label='django_celery_beat', model_name='PeriodicTask'
        )
        PeriodicTask = apps.get_model(
            app_label='django_celery_beat', model_name='PeriodicTask'
        )

        new_source = not self.pk
        with transaction.atomic():
            if not new_source:
                self._delete_periodic_task()

            # Create a new interval or use an existing one
            interval_instance, created = IntervalSchedule.objects.get_or_create(
                every=self.interval, period='seconds'
            )

            PeriodicTask.objects.create(
                name=self._get_periodic_task_name(),
                interval=interval_instance,
                task='mayan.apps.sources.tasks.task_check_interval_source',
                kwargs=json.dumps(obj={'source_id': self.pk})
            )
