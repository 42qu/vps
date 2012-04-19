from time import sleep

class Handler(object):
    def __init__(self, route, host_id):
        self.route = route
        self.host_id = host_id

    def __call__(self, client):
        route = self.route
        host_id = self.host_id

        while True:
            task = client.todo(host_id)
            cmd = task.cmd
            if cmd:
                func = route.get(cmd)
                if func:
                    func(client, task.id)
                    client.done(host_id, task)
            sleep(5)

