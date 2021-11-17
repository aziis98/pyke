
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
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
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
        self.data['checksums'].clear()

    def set_checksum(self, path, value):
        self.data['checksums'][path] = value

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

    def build_target(self, target=None):
        if target == None:
            target = self.rules[list(self.rules)[-1]].target

        rule = self.resolve_target(target)

        if not rule:
            logger.warning(f'No rule found for "{target}", skipping')
            return
        
        # First try build all sources recursively 
        for source in rule.sources:
            self.build(source)

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
            
            self.cache.save()
        else:
            logger.info(f'Target "{target}" is up to date')

    def build(self, target=None):
        own_hash = get_file_checksum("pykefile.py")
        own_old_hash = self.cache.get_checksum("pykefile.py")

        if own_hash != own_old_hash:
            self.cache.clear()
            self.cache.set_checksum("pykefile.py", own_hash)
            self.cache.save()

        self.build_target(target)
