
@rule('a', ['c'])
def _(target, source, sources):
    print("A")

@rule('b', ['a'])
def _(target, source, sources):
    print("B")

@rule('c', ['b'])
def _(target, source, sources):
    print("C")
