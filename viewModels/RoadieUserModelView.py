from viewModels.RoadieModelView import RoadieModelView

class RoadieUserModelView(RoadieModelView):

    form_excluded_columns = ('password')

    column_list = ('username', 'email', 'registeredOn', 'lastUpdated', 'lastLogin')

