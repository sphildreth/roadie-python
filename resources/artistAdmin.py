from flask_admin import BaseView, expose


class ArtistAdmin(BaseView):

    @expose('/artist')
    def index(self):
        users = api.get_users()
        return self.render('custom_template.html', users=users)
