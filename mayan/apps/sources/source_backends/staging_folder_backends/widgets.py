from mayan.apps.documents.widgets import ThumbnailWidget


class StagingFileThumbnailWidget(ThumbnailWidget):
    container_class = 'staging-file-thumbnail-container'
    gallery_name = 'sources:staging_list'
