from viewModels.RoadieModelView import RoadieModelView


class RoadieTrackModelView(RoadieModelView):
    form_ajax_refs = {
        'artist': {
            'fields': ['name'],
            'page_size': 10
        }
    }
