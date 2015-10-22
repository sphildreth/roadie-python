from viewModels.RoadieModelView import RoadieModelAdminRequiredView

class RoadieUserArtistModelView(RoadieModelAdminRequiredView):

    form_ajax_refs = {
        'artist': {
            'fields': ['name'],
            'page_size': 10
        }
    }


