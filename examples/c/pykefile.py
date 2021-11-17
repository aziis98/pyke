
from os import system as run
from pyke import *

p = Pykefile()

@p.rule('%.o', ['%.c'])
def _(target, source, sources):
    run(f'gcc -c {source} -o {target}')

@p.rule('main', ['main.o', 'util.o'])
def _(target, source, sources):
    run(f'gcc -o {target} {" ".join(sources)}')

p.build()
