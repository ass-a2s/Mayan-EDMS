from django.db import models


class SourceManager(models.Manager):
    def interactive(self):
        interactive_sources_ids = []
        for source in self.all():
            if getattr(source.get_backend(), 'is_interactive', False):
                interactive_sources_ids.append(source.pk)

        return self.filter(id__in=interactive_sources_ids)
