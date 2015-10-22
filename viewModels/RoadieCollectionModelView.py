from viewModels.RoadieModelView import RoadieModelView


class RoadieCollectionModelView(RoadieModelView):
    form_subdocuments = {
        'releases': {
            'form_subdocuments': {
                None: {
                    'form_ajax_refs': {
                        'release': {
                            'fields': ['title'],
                            'page_size': 10
                        }
                    }
                }
            }
        }
    }

    form_ajax_refs = {
        'user': {
            'fields': ['username'],
            'page_size': 10
        }
    }
