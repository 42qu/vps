#coding:utf-8

from saas.ttypes import Action, Todo

class Handler(object):
    def todo(self, host_id):
        return Todo(Action.OPEN, 0)

    def info(self, vps_id):
        pass

    def done(self, todo):
        print "done", todo.action , todo.id

if __name__ == "__main__":
    pass

