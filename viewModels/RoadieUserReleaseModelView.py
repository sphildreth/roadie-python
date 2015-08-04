from viewModels.RoadieModelView import RoadieModelView


class RoadieUserReleaseModelView(RoadieModelView):

    form_ajax_refs = {
        'Release': {
            'fields': ['Title'],
            'page_size': 10
        }
    }
