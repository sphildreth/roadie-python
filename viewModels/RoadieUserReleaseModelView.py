from viewModels.RoadieModelView import RoadieModelAdminRequiredView


class RoadieUserReleaseModelView(RoadieModelAdminRequiredView):

    form_ajax_refs = {
        'Release': {
            'fields': ['Title'],
            'page_size': 10
        }
    }
