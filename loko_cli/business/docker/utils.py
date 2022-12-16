import os


def prepare_docker_ignore(path):
    dockerignore = os.path.join(path, '.dockerignore')
    exclude = None
    if os.path.exists(dockerignore):
        with open(dockerignore) as f:
            exclude = list(filter(
                lambda x: x != '' and x[0] != '#',
                [l.strip() for l in f.read().splitlines()]
            ))
    return exclude


def search_key(d, k):
    if isinstance(d, dict):
        if k in d:
            return d[k]
        else:
            for k1, v in d.items():
                ret = search_key(v, k)
                if ret:
                    return ret
            return None
    else:
        return None


class DictVal(dict):
    def __call__(self, obj):
        if not isinstance(obj, dict):
            return False
        for k in self:
            if not self[k](obj.get(k)):
                return False
        return True


class TypeValidator:
    def __init__(self, _type):
        self._type = _type

    def __call__(self, obj):
        return isinstance(obj, self._type)
