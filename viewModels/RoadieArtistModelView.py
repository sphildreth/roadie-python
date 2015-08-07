from viewModels.RoadieModelView import RoadieModelView

class RoadieArtistModelView(RoadieModelView):

    form_excluded_columns = ('Rating')

    form_ajax_refs = {
        'AssociatedArtists': {
            'fields': ['Name'],
            'page_size': 10
        }
    }
