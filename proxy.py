import collections
import sys
from types import (FunctionType, MethodType, GetSetDescriptorType,
                   MemberDescriptorType, ModuleType, LambdaType)
IGNORE = (FunctionType, LambdaType, MemberDescriptorType, ModuleType,
          GetSetDescriptorType, MethodType)



NoneType = type(None)
BooleanType = type(True)
IntType = type(2)
LongType = type(sys.maxsize+1)
FloatType = type(3.1415)
StringType = type("hello")
UnicodeType = type("hello")
TupleType = type((1, 2))
ListType = type([1, 2])
DictType = type({1: 2})
SetType = type({1, 2})
ObjectType = object

PROXY_CLASSES = {}

def get_proxy_class(cls):
    proxy_cls = PROXY_CLASSES.get(cls.__name__, None)
    if proxy_cls:
        return proxy_cls
    else:
        proxy_cls = build_proxy_class(cls)
        PROXY_CLASSES[cls.__name__] = proxy_cls
        return proxy_cls

def build_proxy_class(cls):
    #print "build_proxy_class", cls
    name = "Proxy%s" % cls.__name__
    bases = tuple([ProxyObject, cls] + list(cls.__bases__))
    #no_copy = ['__init__', '__repr__', '__getattr__']
    #classdict = {k: v for k, v in cls.__dict__.items() if isinstance(v, types.FunctionType) and not k in no_copy}
    #classdict = {proxify(k): proxify(v) for k, v in cls.__dict__.items()}
    #for attr in ('__init__', '__repr__', '__getattr__'):
    #    if attr in classdict:
    #        del classdict[attr]
    #print classdict
    return type(name, bases, {})#classdict)



def proxify(obj, memo=None):

    obj_type = type(obj)
    obj_bases = obj_type.__bases__ if hasattr(obj_type, '__bases__') else ()

    if obj_type in (IntType, BooleanType, FloatType, LongType,
                    NoneType, StringType, UnicodeType):
        return obj

    for pt in PROXY_TYPES:
        if pt in obj_bases:
            return obj



    id_obj = id(obj)
    if memo == None:
        memo = {}

    if id_obj in memo:
        return memo[id_obj]

    if obj_type == TupleType:
        value = ProxyTuple(obj, memo)
    elif obj_type == ListType:
        value = ProxyList(obj, memo)
    elif obj_type == DictType or obj_type == collections.defaultdict:
        value = ProxyDict(obj, memo)
    elif obj_type == SetType:
        value = ProxySet(obj, memo)
    elif isinstance(obj, ObjectType):
        if obj_type in IGNORE:
            value = obj
        else:
            value = get_proxy_class(obj.__class__)(obj, memo)
    else:
        print("proxify_other", obj, obj_type, obj_bases)
        value = obj

    memo[id_obj] = value
    return value

class ProxyObject(object):
    def __init__(self, obj, memo):
        self._obj = obj
        self._memo = memo

    def __getattr__(self, key):
        if hasattr(self._obj, key):
            value = proxify(getattr(self._obj, key), self._memo)
            setattr(self, key, value)
            return value
        raise AttributeError

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, repr(self._obj))

class ProxyTuple(collections.Sequence):
    def __init__(self, obj, memo):
        self._obj = obj
        self._modified = False
        self._memo = memo

    def _modify(self):
        if not self._modified:
            self._obj = tuple(proxify(x, self._memo) for x in self._obj)
            self._modified = True

    def __eq__(self, other):
        return self._obj == other

    def __contains__(self, key):
        return key in self._obj

    def __iter__(self):
        self._modify()
        return iter(self._obj)

    def __len__(self):
        return len(self._obj)

    def __getitem__(self, key):
        self._modify()
        return self._obj[key]

    def __hash__(self):
        return hash(self._obj)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, repr(self._obj))

class ProxyList(collections.MutableSequence):
    def __init__(self, obj, memo):
        self._obj = obj
        self._modified = False
        self._memo = memo

    def _modify(self):
        if not self._modified:
            self._obj = [proxify(x, self._memo) for x in self._obj]
            self._modified = True

    def __contains__(self, other):
        return other in self._obj

    def __iter__(self):
        self._modify()
        return iter(self._obj)

    def __len__(self):
        return len(self._obj)

    def __getitem__(self, key):
        self._modify()
        return self._obj[key]

    def __setitem__(self, key, value):
        self._modify()
        return self._obj.__setitem__(key, value)

    def __delitem__(self, key):
        self._modify()
        return self._obj.__delitem__(key)

    def insert(self, key, value):
        self._modify()
        return self._obj.insert(key, value)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, repr(self._obj))

class ProxySet(collections.MutableSet):
    def __init__(self, obj, memo):
        self._obj = obj
        self._modified = False
        self._memo = memo

    def _modify(self):
        if not self._modified:
            self._obj = set(proxify(x, self._memo) for x in self._obj)
            self._modified = True

    def __contains__(self, key):
        return key in self._obj

    def __len__(self):
        return len(self._obj)

    def __iter__(self):
        self._modify()
        return iter(self._obj)

    def add(self, key):
        self._modify()
        return self._obj.add(key)

    def discard(self, key):
        self._modify()
        return self._obj.discard(key)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, repr(self._obj))

    def __hash__(self):
        return hash(self._obj)

class ProxyDict(collections.MutableMapping):
    def __init__(self, obj, memo):
        self._obj = obj
        self._modified = False
        self._memo = memo
        if hasattr(self._obj, "default_factory"):
            self._default = self._obj.default_factory
        else:
            self._default = None

    def _modify(self):
        if not self._modified:
            if self._default:
                newobj = collections.defaultdict(self._default)
                newobj.update({proxify(k, self._memo): proxify(v, self._memo) for k, v in self._obj.items()})
                self._obj = newobj
            else:
                self._obj = {proxify(k, self._memo): proxify(v, self._memo) for k, v in self._obj.items()}
            self._modified = True

    def __contains__(self, key):
        return key in self._obj

    def __iter__(self):
        self._modify()
        return iter(self._obj)

    def __len__(self):
        return len(self._obj)

    def __getitem__(self, key):
        self._modify()
        return self._obj[key]

    def __setitem__(self, key, value):
        self._modify()
        return self._obj.__setitem__(key, value)

    def __delitem__(self, key):
        self._modify()
        return self._obj.__delitem__(key)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, repr(self._obj))

PROXY_TYPES = (ProxyObject, ProxyTuple, ProxyList, ProxyDict, ProxySet)
