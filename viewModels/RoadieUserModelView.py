from viewModels.RoadieModelView import RoadieModelView

class RoadieUserModelView(RoadieModelView):

    form_excluded_columns = ('Password')

    column_list = ('Username','Email', 'RegisteredOn','LastUpdated','LastLogin')

