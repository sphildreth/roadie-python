from viewModels.RoadieModelView import RoadieModelView


class RoadieCollectionModelView(RoadieModelView):
    form_excluded_columns = ('collectionreleases')

    form_ajax_refs = {
        'user': {
            'fields': ['username'],
            'page_size': 10
        }
    }
