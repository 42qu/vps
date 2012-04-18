from time import sleep

class Handler(object):
    def __init__(self, route, host_id):
        self.route = route
        self.host_id = host_id

    def __call__(self, client):
        route = self.route
        host_id = self.host_id

        while True:
            todo = client.todo(host_id)
            action = todo.action
            if action:
                func = route.get(todo.action)
                if func:
                    func(client, todo.id)

            sleep(5)

