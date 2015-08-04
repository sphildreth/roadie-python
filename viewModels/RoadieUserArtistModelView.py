from viewModels.RoadieModelView import RoadieModelView


class RoadieUserArtistModelView(RoadieModelView):

    form_ajax_refs = {
        'Artist': {
            'fields': ['Name'],
            'page_size': 10
        }
    }
