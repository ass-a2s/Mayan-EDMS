import logging
import subprocess

from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from mayan.apps.storage.utils import TemporaryFile

from ..classes import PseudoFile, SourceUploadedFile
from ..exceptions import SourceException
from ..literals import (
    SCANNER_ADF_MODE_CHOICES, SCANNER_MODE_CHOICES, SCANNER_MODE_COLOR,
    SCANNER_SOURCE_CHOICES
)
from ..settings import setting_scanimage_path

from .base import InteractiveSource

__all__ = ('SaneScanner',)
logger = logging.getLogger(name=__name__)


class SaneScanner(InteractiveSource):
    can_uncompress = False
    is_interactive = True
    #source_type = SOURCE_CHOICE_SANE_SCANNER

    device_name = models.CharField(
        max_length=255,
        help_text=_('Device name as returned by the SANE backend.'),
        verbose_name=_('Device name')
    )
    mode = models.CharField(
        blank=True, choices=SCANNER_MODE_CHOICES, default=SCANNER_MODE_COLOR,
        help_text=_(
            'Selects the scan mode (e.g., lineart, monochrome, or color). '
            'If this option is not supported by your scanner, leave it blank.'
        ), max_length=16, verbose_name=_('Mode')
    )
    resolution = models.PositiveIntegerField(
        blank=True, null=True, help_text=_(
            'Sets the resolution of the scanned image in DPI (dots per inch). '
            'Typical value is 200. If this option is not supported by your '
            'scanner, leave it blank.'
        ), verbose_name=_('Resolution')
    )
    source = models.CharField(
        blank=True, choices=SCANNER_SOURCE_CHOICES, help_text=_(
            'Selects the scan source (such as a document-feeder). If this '
            'option is not supported by your scanner, leave it blank.'
        ), max_length=32, null=True, verbose_name=_('Paper source')
    )
    adf_mode = models.CharField(
        blank=True, choices=SCANNER_ADF_MODE_CHOICES,
        help_text=_(
            'Selects the document feeder mode (simplex/duplex). If this '
            'option is not supported by your scanner, leave it blank.'
        ), max_length=16, verbose_name=_('ADF mode')
    )

    objects = models.Manager()

    class Meta:
        verbose_name = _('SANE Scanner')
        verbose_name_plural = _('SANE Scanners')
