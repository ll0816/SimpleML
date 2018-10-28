'''
Meta class to auto register new classes
'''
from sqlalchemy.ext.declarative import declarative_base
from abc import ABCMeta

__author__ = 'Elisha Yadgaran'


class Registry(type):
    '''
    Importable class to maintain reference to the global registry
    '''
    registry = {}

    def __new__(cls, name, bases, attrs):
        new_cls = type.__new__(cls, name, bases, attrs)
        if cls.__name__ in cls.registry:
            raise ValueError('Cannot duplicate class in registry: {}'.format(cls.__name__))
        cls.registry[new_cls.__name__] = new_cls
        return new_cls

    @classmethod
    def get_from_registry(cls, class_name):
        return cls.registry.get(class_name)

    @classmethod
    def get(mcs, class_name):
        return mcs.get_from_registry(class_name)

    @classmethod
    def is_registered(cls, class_name):
        return class_name in cls.registry.keys()

    @classmethod
    def print_all_classes(cls):
        for class_name, c in cls.registry.items():
            print("Class Name: {} -> Class Object: {}\n".format(class_name, c))

# Importable registry
# NEED to use consistent import pattern, otherwise will refer to different memory objects
# from meta_register import SIMPLEML_REGISTRY as s1 != from simpleml.persistables.meta_register import SIMPLEML_REGISTRY as s2

# Need to explicitly merge metaclasses to avoid conflicts
MetaBase = type(declarative_base())


class MetaRegistry(MetaBase, ABCMeta, Registry):
    '''
    TBD on implementing registry as class attribute

    def __init__(cls, name, bases, nmspc):
        super(MetaRegistry, cls).__init__(name, bases, nmspc)

        if not hasattr(cls, 'registry'):
            cls.registry = set()

        cls.registry.add(cls)

        # Remove base classes
        cls.registry -= set(bases)

    def __iter__(cls):
        return iter(cls.registry)
    '''
