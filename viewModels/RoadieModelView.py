import datetime
from flask_admin.contrib.mongoengine import ModelView
from flask.ext.login import LoginManager, login_user, logout_user, \
    current_user, login_required
from widgets.ckeditor import CKTextAreaField
from flask import redirect, url_for, request

class RoadieModelView(ModelView):
    form_overrides = {
        'body': CKTextAreaField
    }
    create_template = 'ckeditor.html'
    edit_template = 'ckeditor.html'

    def on_model_change(self, form, model, is_created):
        if 'LastUpdated' in model:
            model.LastUpdated = datetime.datetime.now()

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.is_editor():
            return True

        return False

    def _handle_view(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        if not self.is_accessible():
            return redirect(url_for('login', next=request.url))


class RoadieModelAdminRequiredView(RoadieModelView):

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('Admin'):
            return True

        return False