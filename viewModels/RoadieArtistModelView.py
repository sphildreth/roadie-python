from viewModels.RoadieModelView import RoadieModelView

class RoadieArtistModelView(RoadieModelView):

    form_excluded_columns = ('rating')

    form_ajax_refs = {
        'associatedArtists': {
            'fields': ['name'],
            'page_size': 10
        }
    }
