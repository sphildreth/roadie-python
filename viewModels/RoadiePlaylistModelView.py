from viewModels.RoadieModelView import RoadieModelView


class RoadiePlaylistModelView(RoadieModelView):
    form_ajax_refs = {
        'user': {
            'fields': ['username'],
            'page_size': 10
        },
    }

    # form_ajax_refs = {
    #     'user': {
    #         'fields': ['username'],
    #         'page_size': 10
    #     },
    #     'tracks': {
    #         'fields': ['title'],
    #         'page_size': 10
    #     }
    # }
