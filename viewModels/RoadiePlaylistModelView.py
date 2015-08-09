from viewModels.RoadieModelView import RoadieModelView


class RoadiePlaylistModelView(RoadieModelView):

    form_ajax_refs = {
        'User': {
            'fields': ['Username'],
            'page_size': 10
        },
        'Tracks': {
            'fields': ['Title'],
            'page_size': 10
        }
    }
