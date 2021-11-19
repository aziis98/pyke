
import logging
import os
import json
import inspect

def test_pattern(pattern, path):
    symbol_index = pattern.find("%")
    before_generic = pattern[:symbol_index]
    after_generic = pattern[symbol_index + 1:]

    if path.startswith(before_generic) and path.endswith(after_generic):
        match = path[len(before_generic):len(path) - len(after_generic)]
        if len(match) == 0:
            return True
        else: 
            return match
    
    return False

def get_file_checksum(path):
    if not os.path.exists(path):
        return None

    return os.popen(f'md5sum "{path}" | cut -d" " -f 1').read().strip()

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'))

logger.addHandler(ch)

class Rule:
    def __init__(self, target, sources, make):
        self.target = target
        self.sources = sources
        self.make = make
    
    def __repr__(self):
        return f"Rule('{self.target}', {self.sources}, {self.make})"

    def show(self):
        return f'\n{inspect.getsource(self.make)}'

class ConcreteRule:
    def __init__(self, rule, matched_part):
        self.rule = rule
        self.matched_part = matched_part
        self.target = rule.target.replace("%", matched_part)
        self.sources = [
            source.replace("%", matched_part) for source in rule.sources
        ]
    
    def make(self, target, source, sources):
        self.rule.make(self.target, self.sources[0], self.sources)

    def show(self):
        return f'\n% = "{self.matched_part}"{self.rule.show()}'

class PykefileCache:
    def __init__(self, base_path):
        self.path = f"{base_path}/.pykecache.json"
        self.data = {
            'version': 1,
            'checksums': dict()
        }

        if os.path.exists(self.path):
            self.load()
        else:
            self.save()

    def load(self):
        content = open(self.path, 'r').read()
        self.data = json.loads(content)

    def save(self):
        content = json.dumps(self.data, indent=2)
        open(self.path, "w").write(content)

    def clear(self):
        logger.debug(f'Updating clearing checksum cache')
        self.data['checksums'].clear()
        self.save()

    def set_checksum(self, path, value):
        logger.debug(f'Updating checksum of "{path}"')
        self.data['checksums'][path] = value
        self.save()

    def get_checksum(self, path):
        if path not in self.data['checksums']:
            return False

        return self.data['checksums'][path]

class Pykefile:
    def __init__(self):
        self.rules = dict()
        self.path = os.getcwd()
        self.cache = PykefileCache(self.path)

    def rule(self, target, sources):
        def wrapper(make):
            rule = Rule(target, sources, make)
            logger.debug(f"Registered {rule}")
            self.rules[target] = rule
    
        return wrapper

    # Tries to find a rule to produce the given target. Supports the "%" Makefile syntax
    def resolve_target(self, target):
        for rule in self.rules.values():
            m = test_pattern(rule.target, target)

            if m == True:
                return rule
            elif type(m) == str:
                return ConcreteRule(rule, m)

        return None

    def build_target(self, target=None, trace=[]):
        if target == None:
            target = self.rules[list(self.rules)[-1]].target

        # TODO: Maybe compute hash by concatenating the hashes of its children.
        if os.path.isdir(target):
            logger.error(f'Can\'t build "{target}", it\'s already a directory')
            exit(1)

        if target in trace:
            logger.error(f'Found dependency cycle caused by "{target}", aborting! Trace: {trace}')
            exit(1)

        rule = self.resolve_target(target)

        if not rule:
            logger.warning(f'Skipping terminal target "{target}"')
            return
        
        # First try build all sources recursively 
        for source in rule.sources:
            self.build_target(source, [*trace, target])

        # TODO: This step can be easily parallelized
        sources_checksums = { path: get_file_checksum(path) for path in rule.sources }
        sources_old_checksums = { path: self.cache.get_checksum(path) for path in rule.sources }

        if sources_checksums != sources_old_checksums:
            logger.info(f'Making target "{target}"')
            logger.info(f'Running...\n{rule.show()}')

            rule.make(rule.target, rule.sources[0], rule.sources)

            # Updates the checksums of the source files of this target
            for path, value in sources_checksums.items():
                self.cache.set_checksum(path, value)
        else:
            logger.info(f'Target "{target}" is up to date')

    def build(self, target=None, force=False):
        own_hash = get_file_checksum("pykefile.py")
        own_old_hash = self.cache.get_checksum("pykefile.py")

        if force or own_hash != own_old_hash:
            self.cache.clear()
            self.cache.set_checksum("pykefile.py", own_hash)

        self.build_target(target)

HELP_TEXT="""
Usage: pyke [-f|--force] [-v|-vv|-vvv] [-h|--help] TARGETS...

A small clone of GNU Make with a python build script that
recompiles targets based on their checksums.

If no TARGETS are present then the last recipe is used as
a starting point.

Options:
  -f, --force   Clean the checksum to force recompilation 
                of all given targets
  -h, --help    Shows this message
  -v            Logs warning, by default only errors are printed 
  -vv           Also logs info level messages
  -vvv          Also logs debug messages
"""

def build_with_args(pykefile, argv):
    logger.setLevel(logging.ERROR)
    
    targets = []
    force = False

    args = argv[1:]
    while len(args) > 0:
        if args[0] == '--force' or args[0] == '-f':
            args.pop(0)
            force = True
        elif args[0] == '-v':
            args.pop(0)
            logger.setLevel(logging.WARNING)
        elif args[0] == '-vv':
            args.pop(0)
            logger.setLevel(logging.INFO)
        elif args[0] == '-vvv':
            args.pop(0)
            logger.setLevel(logging.DEBUG)
        elif args[0] == '--help' or args[0] == '-h':
            print(HELP_TEXT)
            exit(0)
        else:
            targets.append(args.pop(0))

    [logger.debug(f'Registered {rule}') for rule in pykefile.rules.values()]

    if len(targets) == 0:
        pykefile.build(force=force)
    else:
        for target in targets:
            pykefile.build(target, force)

