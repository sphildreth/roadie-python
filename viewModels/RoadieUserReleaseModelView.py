from viewModels.RoadieModelView import RoadieModelAdminRequiredView


class RoadieUserReleaseModelView(RoadieModelAdminRequiredView):

    form_ajax_refs = {
        'release': {
            'fields': ['title'],
            'page_size': 10
        }
    }
