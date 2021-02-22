from ..permissions import permission_document_view
from ..widgets import BaseDocumentThumbnailWidget

from .base import GenericDocumentViewTestCase
from .mixins.document_mixins import DocumentViewTestMixin


class DocumentFilePageWidgetTestCase(GenericDocumentTestCase):
    def test_document_list_view_document_with_no_pages(self):
        thumbnail_widget = BaseDocumentThumbnailWidget()
        self.test_document.pages.all().delete()
        result = thumbnail_widget.render(instance=self.test_document)

        self.assertTrue(self.test_document.get_absolute_url() in result)


class DocumentPreviewWidgetViewTestCase(
    DocumentViewTestMixin, GenericDocumentViewTestCase
):
    def test_document_preview_page_carousel_widget_render(self):
        self.grant_access(
            obj=self.test_document, permission=permission_document_view
        )

        response = self._request_test_document_preview_view()
        self.assertContains(
            response=response, status_code=200, text='carousel-container'
        )
