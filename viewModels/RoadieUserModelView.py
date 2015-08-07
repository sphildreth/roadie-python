from viewModels.RoadieModelView import RoadieModelView
from flask.ext.login import current_user


class RoadieUserModelView(RoadieModelView):

    form_excluded_columns = ('Password')

