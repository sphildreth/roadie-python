from flask_admin.contrib.sqla import ModelView
import os
import json
from resources.id3 import ID3

from viewModels.RoadieModelView import RoadieModelView

class RoadieReleaseModelView(RoadieModelView):
    form_subdocuments = {
        'labels': {
            'form_subdocuments': {
                None: {
                    'form_ajax_refs': {
                        'Label': {
                            'fields': ['name'],
                            'page_size': 10
                        }
                    }
                }
            }
        },
        'tracks': {
            'form_subdocuments': {
                None: {
                    'form_ajax_refs': {
                        'Track': {
                            'fields': ['title'],
                            'page_size': 10
                        }
                    }
                }
            }
        }
    }

    form_ajax_refs = {
        'artist': {
            'fields': ['name'],
            'page_size': 10
        }
    }

    def on_model_change(self, form, model, is_created):
        try:
            # Get the config and see if saving to tags is enabled if so then update appropriate tags for release
            appPath = '\\'.join(os.path.realpath(__file__).split('\\')[0:4])
            with open(os.path.join(appPath, "settings.json"), "r") as rf:
                config = json.load(rf)
            processingOptions = None
            if 'ROADIE_PROCESSING' in config:
                processingOptions = config['ROADIE_PROCESSING']
            if processingOptions and 'DoSaveEditsToTags' in processingOptions:
                if processingOptions['DoSaveEditsToTags'].lower() == "true":
                    for track in model.Tracks:
                        trackPath = os.path.join(track.Track.FilePath, track.Track.FileName)
                        id3 = ID3(trackPath, config)
                        id3.updateFromRelease(model, track)
        except:
            pass
        # Call the base class to update any necessary timestamps and such
        super(RoadieReleaseModelView, self).on_model_change(form,model,is_created)