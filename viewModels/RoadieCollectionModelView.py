from viewModels.RoadieModelView import RoadieModelView


class RoadieCollectionModelView(RoadieModelView):
    form_subdocuments = {
        'Releases': {
            'form_subdocuments': {
                None: {
                    'form_ajax_refs': {
                        'Release': {
                            'fields': ['Title'],
                            'page_size': 10
                        }
                    }
                }
            }
        }
    }

    form_ajax_refs = {
        'Maintainer': {
            'fields': ['Username'],
            'page_size': 10
        }
    }
