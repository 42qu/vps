#coding:utf-8

from saas.ttypes import Action
from time import sleep
from config import HOST_ID

def handler(client):
    while True:
        todo = client.todo(HOST_ID)
        if todo.action:
            pass 
        print todo.action , to.id
        sleep(10)


if __name__ == "__main__":
    pass

