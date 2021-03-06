'''
Wrapper class for a pickleable pipeline of a series of transformers
'''

from collections import OrderedDict
from sklearn.pipeline import Pipeline

__author__ = 'Elisha Yadgaran'


class DefaultPipeline(OrderedDict):
    '''
    Use default dictionary behavior but add wrapper methods for
    extended functionality
    '''
    def add_transformer(self, name, transformer):
        '''
        Setter method for new transformer step
        '''
        self[name] = transformer

    def remove_transformer(self, name):
        '''
        Delete method for transformer step
        '''
        del self[name]

    def fit(self, X, y=None, **kwargs):
        '''
        Iterate through each transformation step and apply fit
        '''
        for step, transformer in self.iteritems():
            X = transformer.fit_transform(X, y=y, **kwargs)

        return self

    def transform(self, X, y=None, **kwargs):
        '''
        Iterate through each transformation step and apply transform
        '''
        for step, transformer in self.iteritems():
            X = transformer.transform(X, y=y, **kwargs)

        return X

    def fit_transform(self, X, y=None, **kwargs):
        '''
        Iterate through each transformation step and apply fit and transform
        '''
        for step, transformer in self.iteritems():
            X = transformer.fit_transform(X, y=y, **kwargs)

        return X

    def get_params(self, **kwargs):
        '''
        Iterate through transformers and return parameters
        '''
        params = {}
        for step, transformer in self.iteritems():
            params[step] = transformer.get_params(**kwargs)

        return params

    def set_params(self, **params):
        '''
        Set params for transformers. Input is expected to be dict of dict

        :param params: dictionary of dictionaries. each dictionary must map to
        a transformer step
        '''
        for step, param in params.iteritems():
            self[step].set_params(**param)

    def get_transformers(self):
        '''
        Get list of (step, transformer) tuples
        '''
        return [(i, j.__class__.__name__) for i, j in self.items()]

    def get_feature_names(self, feature_names):
        '''
        Iterate through each transformer and return list of resulting features
        starts with empty list by default but can pass in dataset as starting
        point to guide transformations

        :param feature_names: list of initial feature names before transformations
        :type: list
        '''
        for step, transformer in self.iteritems():
            feature_names = transformer.get_feature_names(feature_names)

        return feature_names


class SklearnPipeline(Pipeline):
    '''
    Use default sklearn behavior but add wrapper methods for
    extended functionality
    '''
    def add_transformer(self, name, transformer, index=None):
        '''
        Setter method for new transformer step
        '''
        if index is not None:
            self.steps.insert(index, (name, transformer))
        else:
            self.steps.append((name, transformer))

    def remove_transformer(self, name):
        '''
        Delete method for transformer step
        '''
        index = [i for i, j in enumerate(self.steps) if j[0] == name][0]
        self.steps.pop(index)

    def get_transformers(self):
        '''
        Get list of (step, transformer) tuples
        '''
        return [(i, j.__class__.__name__) for i, j in self.steps]

    def get_feature_names(self, feature_names):
        '''
        Iterate through each transformer and return list of resulting features
        starts with empty list by default but can pass in dataset as starting
        point to guide transformations

        :param feature_names: list of initial feature names before transformations
        :type: list
        '''
        for step, transformer in self.steps:
            feature_names = transformer.get_feature_names(feature_names)

        return feature_names
