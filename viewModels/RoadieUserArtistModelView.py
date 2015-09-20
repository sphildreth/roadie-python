from viewModels.RoadieModelView import RoadieModelAdminRequiredView

class RoadieUserArtistModelView(RoadieModelAdminRequiredView):

    form_ajax_refs = {
        'Artist': {
            'fields': ['Name'],
            'page_size': 10
        }
    }


