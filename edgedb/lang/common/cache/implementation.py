##
# Copyright (c) 2011 Sprymix Inc.
# All rights reserved.
#
# See LICENSE for details.
##


import pickle
from datetime import timedelta

from semantix.utils import abc
from semantix.utils.algos.persistent_hash import persistent_hash
from . import provider, exceptions

from semantix.utils.storage import abstract as abstract_storage


class AbstractImplementation(abstract_storage.Implementation):
    key_hash_function = persistent_hash

    __slots__ = ()

    @abc.abstractmethod
    def getitem(self, key:bytes):
        pass

    @abc.abstractmethod
    def setitem(self, key:bytes, value:bytes, expiry:float=None):
        pass

    @abc.abstractmethod
    def delitem(self, key:bytes):
        pass

    @abc.abstractmethod
    def contains(self, key:bytes):
        pass


class BaseImplementation(AbstractImplementation):
    compatible_provider_classes = (provider.BlockingProvider, provider.NonBlockingProvider)

    __slots__ = ('meths_cache',)

    def __init__(self, providers):
        super().__init__(providers)
        self.meths_cache = {}

    def _provider_method(self, provider, methname):
        try:
            return self.meths_cache[(provider, methname)]
        except KeyError:
            pass

        try:
            meth = getattr(provider, '{}_nonblocking'.format(methname))
        except AttributeError:
            try:
                meth = getattr(provider, '{}_blocking'.format(methname))
            except AttributeError:
                raise exceptions.CacheError('unsupported provider {!r}'.format(provider))

        self.meths_cache[(provider, methname)] = meth
        return meth

    def getitem(self, key):
        for idx, provider in enumerate(self._providers):
            meth = self._provider_method(provider, 'get')

            try:
                value = meth(key)
            except LookupError:
                pass
            else:
                if idx:
                    for i in range(idx):
                        self._providers[i].set(key, value)
                return pickle.loads(value)

        raise KeyError('missing cache key {!r}'.format(key))

    def setitem(self, key, value, expiry=None):
        pickled_value = pickle.dumps(value)

        for provider in self._providers:
            meth = self._provider_method(provider, 'set')
            meth(key, pickled_value, expiry=expiry)

    def delitem(self, key):
        for provider in self._providers:
            meth = self._provider_method(provider, 'delete')
            meth(key)

    def contains(self, key):
        for provider in self._providers:
            meth = self._provider_method(provider, 'contains')

            if meth(key):
                return True

        return False
