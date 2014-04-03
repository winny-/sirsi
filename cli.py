from __future__ import print_function

from sirsi import Account
from tabulate import tabulate
import json
import os.path
import sys


def get_configuration(json_file=None):
    if json_file is None:
        home = os.path.expanduser('~')
        json_file = os.path.join(home, '.sirsi.json')
    with open(json_file, 'rb') as f:
        config = json.load(f)
    return config


def main(args):
    if not args:
        config = get_configuration()
        args = [config['catalog'], config['userid'], config['password']]
    a = Account(catalog=args[0], userid=args[1], password=args[2])
    items = a.items()
    fines = a.fines()
    if len(items) > 1:
        s = 's'
    else:
        s = ''
    print('You have {} item{} checked out. You owe {} in fines.'.format(len(items), s, fines))
    if len(items) < 1:
        return
    print('')
    print('Renewing all items... ', end='')
    print(a.renew_all())
    items = [i[1:] for i in a.items()]
    print('')
    table = tabulate(items, ['Book title', 'Due date', 'Times renewed'])
    print(table)


if __name__ == '__main__':
    args = sys.argv[1:]
    main(args)
