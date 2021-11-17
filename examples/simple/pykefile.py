
from os import system as run
from pyke import *

p = Pykefile()

@p.rule('b.txt', ['a.txt'])
def _(target, source, sources):
    run(f'head -n 3 {source} > {target}')
    run(f'printf "\n" >> {target}')

@p.rule('c.txt', ['b.txt'])
def _(target, source, sources):
    run(f'cat {source} {source} {source} > {target}')

p.build()