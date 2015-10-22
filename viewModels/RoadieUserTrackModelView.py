from viewModels.RoadieModelView import RoadieModelAdminRequiredView


class RoadieUserTrackModelView(RoadieModelAdminRequiredView):

    form_ajax_refs = {
        'release': {
            'fields': ['title'],
            'page_size': 10
        },
        'track': {
            'fields': ['title'],
            'page_size': 10
        }
    }
