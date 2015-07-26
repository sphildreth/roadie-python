from viewModels.RoadieModelView import RoadieModelView


class RoadieReleaseModelView(RoadieModelView):
    form_subdocuments = {
        'Labels': {
            'form_subdocuments': {
                None: {
                    'form_ajax_refs': {
                        'Label': {
                            'fields': ['Name'],
                            'page_size': 10
                        }
                    }
                }
            }
        },
        'Tracks': {
            'form_subdocuments': {
                None: {
                    'form_ajax_refs': {
                        'Track': {
                            'fields': ['Title'],
                            'page_size': 10
                        }
                    }
                }
            }
        }
    }

    form_ajax_refs = {
        'Artist': {
            'fields': ['Name'],
            'page_size': 10
        }
    }
