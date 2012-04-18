#coding:utf-8

from saas.ttypes import Action
from time import sleep
from config import HOST_ID

def handler(client):
    while True:
        action, id = client.to_do(HOST_ID)
        if action:
            print action , id
        sleep(10)


if __name__ == "__main__":
    pass

