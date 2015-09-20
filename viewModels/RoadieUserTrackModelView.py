from viewModels.RoadieModelView import RoadieModelAdminRequiredView


class RoadieUserTrackModelView(RoadieModelAdminRequiredView):

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
