

class Route(object):
    def __init__(self):
        self._ROUTE = {}

    def __call__(self, id):
        def _(func):
            self._ROUTE[id] = func
            return func
        return _

    def get(self, id):
        return self._ROUTE.get(id, None) 

route = Route()
