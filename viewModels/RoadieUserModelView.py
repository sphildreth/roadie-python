from viewModels.RoadieModelView import RoadieModelView
from flask.ext.login import current_user


class RoadieUserModelView(RoadieModelView):

    form_excluded_columns = ('Password')

    @property
    def can_create(self):
        return current_user.has_role('Admin')

    @property
    def can_delete(self):
        return current_user.has_role('Admin')

    def is_accessible(self):
        return current_user.is_active() and current_user.is_authenticated()
