#coding:utf-8

from saas.ttypes import Action

class Handler(object):
    def to_do(self, pc):
        return (Action.OPEN, 0)

    def info(self, id):
        pass

    def opened(self, id):
        pass

    def closed(self, id):
        pass

    def restart(self, id):
        pass

if __name__ == "__main__":
    pass

