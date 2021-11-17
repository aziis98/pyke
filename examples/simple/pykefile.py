
@rule('b.txt', ['a.txt'])
def _(target, source, sources):
    run(f'head -n 3 {source} > {target}')
    run(f'printf "\n" >> {target}')

@rule('c.txt', ['b.txt'])
def _(target, source, sources):
    run(f'cat {source} {source} {source} > {target}')
