#coding:utf-8

from saas.ttypes import Action
from time import sleep


def handler(client):
    while True:
        action, id = client.to_do()
        if action:
            print action , id
        sleep(10)


if __name__ == "__main__":
    pass

