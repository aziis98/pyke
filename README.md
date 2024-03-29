# Pyke

This _weekend project_ is a small clone (most of the code is in [a single file](./pyke.py) of just about 200LoC) of GNU Make with the twist that it rebuilds a target only if the hash of any of its sources changes. This is named **Pyke** as in **Py**thon + Ma**ke** (I have no hope of being the first coming up with this name for a project).

## Usage

### Installation

Clone the project and then install it locally with pip.

```bash shell
$ git clone https://github.com/aziis98/pyke
$ cd pyke
$ pip install -e .
```

### Files

Create a `pykefile.py` in your project folder and add recipes to build your targets (for now just read below and look at the examples for the syntax).

- `pykefile.py`

    The provided globals in this file are

    - `pikefile` is of type `Pikefile` and holds all the rules and handles the building of the project.

    - `rule` is a function and an alias for `pikefile.rule` and is used as a decorator to define new rules.

    - `run` is just an alias for `os.system` used to directly call shell commands.

- `.pykecache.json`

    This file stores the checksums of all built targets.

## Examples

There are some examples in [./examples](./examples).

### [Simple](./examples/simple)

This example shows how the checksums approach is better in this case with respect to Make.

```python
@rule('b.txt', ['a.txt'])
def _(target, source, sources):
    run(f'head -n 3 {source} > {target}')
    run(f'printf "\n" >> {target}')

@rule('c.txt', ['b.txt'])
def _(target, source, sources):
    run(f'cat {source} {source} {source} > {target}')
```

The file `b.txt` depends only on a part of `a.txt` so changes to its end don't trigger the recompilation of targets that depend only on `b.txt`. In this case, Make couldn't have figured that changes to the end of `a.txt` don't affect `b.txt`. 

### [C](./examples/c)

A simple example that shows a generic rule with "`%`" for creating object files from the sources `main.c` and `util.c` and then linking them.

```python
@rule('%.o', ['%.c'])
def _(target, source, sources):
    run(f'gcc -c {source} -o {target}')

@rule('main', ['main.o', 'util.o'])
def _(target, source, sources):
    run(f'gcc -o {target} {" ".join(sources)}')
```

### [Cycle](./examples/cycle)

This example shows the cycle detection feature

```python
@rule('a', ['c'])
def _(target, source, sources):
    print("A")

@rule('b', ['a'])
def _(target, source, sources):
    print("B")

@rule('c', ['b'])
def _(target, source, sources):
    print("C")
```

Trying to execute `pyke` for this project gives 

```
$ pyke
[ERROR] Found dependency cycle caused by "c", aborting! Trace: ['c', 'b', 'a']
```

## TODOs

- Move the code of `pyke.build_with_args()` directly inside `bin/pike` and decouple the logging code in its own module to let the logging level be changed from the start script. 

