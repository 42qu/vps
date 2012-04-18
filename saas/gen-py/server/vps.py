#coding:utf-8

from saas.ttypes import Action, Todo

class Handler(object):
    def to_do(self, host_id):
        return Todo(Action.NONE, 0)

    def info(self, vps_id):
        pass

    def opened(self, vps_id):
        pass

    def closed(self, vps_id):
        pass

    def restart(self, vps_id):
        pass

if __name__ == "__main__":
    pass

