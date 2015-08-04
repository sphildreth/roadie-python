from viewModels.RoadieModelView import RoadieModelView


class RoadieUserTrackModelView(RoadieModelView):

    form_ajax_refs = {
        'Release': {
            'fields': ['Title'],
            'page_size': 10
        },
        'Track': {
            'fields': ['Title'],
            'page_size': 10
        }
    }
