from json.encoder import JSONEncoder
from json.decoder import JSONDecoder
from collections import defaultdict


class GenericJsonEncoder(JSONEncoder):
    def __init__(self, include_class=False, **kwargs):
        JSONEncoder.__init__(self)
        self.include_class = include_class

    def default(self, o):
        if hasattr(o, "__dict__"):
            temp = dict(o.__dict__)
            if self.include_class:
                temp['__class__'] = type(o).__name__
            return temp
        elif hasattr(o, "tolist"):
            return o.tolist()
        else:
            return str(o)


class GenericJsonDecoder(JSONDecoder):
    def __init__(self, klasses):
        self.m = {}
        for k in klasses:
            self.m[k.__name__] = k

    def object_hook(self, dct):
        if "__class__" in dct:
            temp = dict(dct)
            del temp["__class__"]
            return self.m[dct['__class__']](**temp)
        else:
            return dct


def json_friendly(obj):
    if isinstance(obj, dict):
        return {k: json_friendly(v) for (k, v) in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_friendly(v) for v in obj]
    if isinstance(obj, bytes):
        return "(binary)"
    if isinstance(obj, (int, float)):
        return obj

    if hasattr(obj, "__dict__"):
        return json_friendly(obj.__dict__)
    return str(obj)


class IDDict(dict):
    def __init__(self, factory, _id="id"):
        self.factory = factory
        self.objects = {}
        self._id = _id

    def __getid(self, k):
        if isinstance(k, dict):
            return k[self._id]
        if hasattr(k, "__dict__"):
            return getattr(k, self._id)
        return k

    def __getitem__(self, k):
        if self.__getid(k) not in self:
            self[self.__getid(k)] = self.factory()
        return super().__getitem__(self.__getid(k))

    def __setitem__(self, k, v):
        self.objects[self.__getid(k)] = v
        super().__setitem__(self.__getid(k), v)
