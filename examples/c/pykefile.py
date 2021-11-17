
@rule('%.o', ['%.c'])
def _(target, source, sources):
    run(f'gcc -c {source} -o {target}')

@rule('main', ['main.o', 'util.o'])
def _(target, source, sources):
    run(f'gcc -o {target} {" ".join(sources)}')
