'''
Module with helper classes to create new persistables
'''
from abc import ABCMeta, abstractmethod
from simpleml.persistables.meta_registry import SIMPLEML_REGISTRY
from simpleml.datasets.raw_datasets.base_raw_dataset import BaseRawDataset
from simpleml.pipelines.dataset_pipelines.base_dataset_pipeline import BaseDatasetPipeline
from simpleml.datasets.processed_datasets.base_processed_dataset import BaseProcessedDataset
from simpleml.pipelines.production_pipelines.base_production_pipeline import BaseProductionPipeline
from simpleml.models.base_model import BaseModel
from simpleml.metrics.base_metric import BaseMetric
from simpleml.utils.errors import TrainingError
import logging

LOGGER = logging.getLogger(__name__)

__author__ = 'Elisha Yadgaran'


class PersistableCreator(object):
    __metaclass__ = ABCMeta

    @classmethod
    def retrieve_or_create(self, **kwargs):
        '''
        Wrapper method to first attempt to retrieve a matching persistable and
        then create a new one if it isn't found
        '''
        cls, filters = self.determine_filters(**kwargs)
        persistable = self.retrieve(cls, filters)

        if persistable is not None:
            LOGGER.info('Using existing persistable: {}, {}, {}'.format(cls.__tablename__, persistable.name, persistable.version))
            persistable.load()
            return persistable

        else:
            LOGGER.info('Existing persistable not found. Creating new one now')
            persistable = self.create_new(**kwargs)
            LOGGER.info('Using new persistable: {}, {}, {}'.format(cls.__tablename__, persistable.name, persistable.version))
            return persistable

    @staticmethod
    def retrieve(cls, filters):
        '''
        Query database using the table model (cls) and filters for a matching
        persistable
        '''
        return cls.where(**filters).order_by(cls.version.desc()).first()

    @staticmethod
    def retrieve_dependency(dependency_cls, **dependency_kwargs):
        '''
        Base method to query for dependency
        Raises TrainingError if dependency does not exist
        '''
        dependency = dependency_cls.retrieve(
            *dependency_cls.determine_filters(**dependency_kwargs))
        if dependency is None:
            raise TrainingError('Expected dependency is missing')
        dependency.load()
        return dependency

    @abstractmethod
    def determine_filters(strict=False, **kwargs):
        '''
        stateless method to determine which filters to apply when looking for
        existing persistable

        :param strict: whether to fit objects first before assuming they are identical
        In theory if all inputs and classes are the same, the outputs should deterministically
        be the same as well (up to random iter). So, you dont need to fit objects
        to be sure they are the same

        Default design iterates through 2 (or 3) options when retrieving persistables:
            1) By name and version (unique properties that define persistables)
            2) By name, registered_name, and computed hash
            2.5) Optionally, just use name and registered_name (assumes class
                definition is the same and would result in an identical persistable)

        Returns: database class, filter dictionary
        '''

    @abstractmethod
    def create_new(**kwargs):
        '''
        Stateless method to create a new persistable with the desired parameters
        kwargs are passed directly to persistable
        '''


class RawDatasetCreator(PersistableCreator):
    @staticmethod
    def determine_filters(name='', version=None, strict=True, **kwargs):
        '''
        stateless method to determine which filters to apply when looking for
        existing persistable

        Returns: database class, filter dictionary

        :param registered_name: Class name registered in SimpleML
        :param strict: whether to assume same class and name == same persistable,
        or, load the data and compare the hash
        '''
        if version is not None:
            filters = {
                'name': name,
                'version': version
            }
        # Datasets are special because we cannot assert the data is the same until we load it
        elif strict:
            registered_name = kwargs.get('registered_name')
            new_dataset = SIMPLEML_REGISTRY.get(registered_name)(name=name, **kwargs)
            filters = {
                'name': name,
                'registered_name': registered_name,
                'hash_': new_dataset._hash()
            }

        else:
            filters =  {
                'name': name,
                'registered_name': kwargs.get('registered_name')
            }

        return BaseRawDataset, filters

    @staticmethod
    def create_new(registered_name, **kwargs):
        '''
        Stateless method to create a new persistable with the desired parameters
        kwargs are passed directly to persistable

        :param registered_name: Class name registered in SimpleML
        '''
        new_dataset = SIMPLEML_REGISTRY.get(registered_name)(**kwargs)
        new_dataset.build_dataframe()
        new_dataset.save()

        return new_dataset


class DatasetPipelineCreator(PersistableCreator):
    @classmethod
    def determine_filters(cls, name='', version=None, strict=False, **kwargs):
        '''
        stateless method to determine which filters to apply when looking for
        existing persistable

        Returns: database class, filter dictionary

        :param registered_name: Class name registered in SimpleML
        :param strict: whether to fit objects first before assuming they are identical
        In theory if all inputs and classes are the same, the outputs should deterministically
        be the same as well (up to random iter). So, you dont need to fit objects
        to be sure they are the same
        '''
        if version is not None:
            filters = {
                'name': name,
                'version': version
            }

        else:
            # Check if dependency object was passed
            dataset = kwargs.pop('raw_dataset', None)
            if dataset is None:
                # Use dependency reference to retrieve object
                dataset = cls.retrieve_dataset(**kwargs.pop('raw_dataset_kwargs', {}))

            # Build dummy object to retrieve hash to look for
            registered_name = kwargs.pop('registered_name')
            new_pipeline = SIMPLEML_REGISTRY.get(registered_name)(name=name, **kwargs)
            new_pipeline.add_dataset(dataset)
            if strict:
                new_pipeline.fit()

            filters = {
                'name': name,
                'registered_name': registered_name,
                'hash_': new_pipeline._hash()
            }

        return BaseDatasetPipeline, filters

    @classmethod
    def create_new(cls, registered_name, raw_dataset=None, **kwargs):
        '''
        Stateless method to create a new persistable with the desired parameters
        kwargs are passed directly to persistable

        :param registered_name: Class name registered in SimpleML
        :param raw_dataset: raw dataset object
        '''
        if raw_dataset is None:
            # Use dependency reference to retrieve object
            raw_dataset = cls.retrieve_dataset(**kwargs.pop('raw_dataset_kwargs', {}))

        new_pipeline = SIMPLEML_REGISTRY.get(registered_name)(**kwargs)
        new_pipeline.add_dataset(raw_dataset)
        new_pipeline.fit()
        new_pipeline.save()

        return new_pipeline

    @classmethod
    def retrieve_dataset(cls, **dataset_kwargs):
        return cls.retrieve_dependency(RawDatasetCreator, **dataset_kwargs)


class DatasetCreator(PersistableCreator):
    @classmethod
    def determine_filters(cls, name='', version=None, strict=True, **kwargs):
        '''
        stateless method to determine which filters to apply when looking for
        existing persistable

        Returns: database class, filter dictionary

        :param registered_name: Class name registered in SimpleML
        :param strict: whether to assume same class and name = same persistable,
        or, load the data and compare the hash
        '''

        if version is not None:
            filters = {
                'name': name,
                'version': version
            }

        else:
            registered_name = kwargs.pop('registered_name')
            # Check if dependency object was passed
            dataset_pipeline = kwargs.pop('dataset_pipeline', None)

            if dataset_pipeline is None:
                # Use dependency reference to retrieve object
                dataset_pipeline = cls.retrieve_pipeline(**kwargs.pop('dataset_pipeline_kwargs', {}))

            if strict:
                # Build dummy object to retrieve hash to look for
                new_dataset = SIMPLEML_REGISTRY.get(registered_name)(name=name, **kwargs)
                new_dataset.add_pipeline(dataset_pipeline)
                new_dataset.build_dataframe()

                filters = {
                    'name': name,
                    'registered_name': registered_name,
                    'hash_': new_dataset._hash()
                }

            else:
                # Assume combo of name, class, and pipeline will be unique
                filters =  {
                    'name': name,
                    'registered_name': registered_name,
                    'pipeline_id': dataset_pipeline.id
                }

        return BaseProcessedDataset, filters

    @classmethod
    def create_new(cls, registered_name, dataset_pipeline=None, **kwargs):
        '''
        Stateless method to create a new persistable with the desired parameters
        kwargs are passed directly to persistable

        :param registered_name: Class name registered in SimpleML
        :param dataset_pipeline: dataset pipeline object
        '''
        if dataset_pipeline is None:
            # Use dependency reference to retrieve object
            dataset_pipeline = cls.retrieve_pipeline(**kwargs.pop('dataset_pipeline_kwargs', {}))

        new_dataset = SIMPLEML_REGISTRY.get(registered_name)(**kwargs)
        new_dataset.add_pipeline(dataset_pipeline)
        new_dataset.build_dataframe()
        new_dataset.save()

        return new_dataset

    @classmethod
    def retrieve_pipeline(cls, **pipeline_kwargs):
        return cls.retrieve_dependency(DatasetPipelineCreator, **pipeline_kwargs)


class PipelineCreator(PersistableCreator):
    @classmethod
    def determine_filters(cls, name='', version=None, strict=False, **kwargs):
        '''
        stateless method to determine which filters to apply when looking for
        existing persistable

        Returns: database class, filter dictionary

        :param registered_name: Class name registered in SimpleML
        :param strict: whether to fit objects first before assuming they are identical
        In theory if all inputs and classes are the same, the outputs should deterministically
        be the same as well (up to random iter). So, you dont need to fit objects
        to be sure they are the same
        '''
        if version is not None:
            filters = {
                'name': name,
                'version': version
            }

        else:
            # Check if dependency object was passed
            dataset = kwargs.pop('dataset', None)
            if dataset is None:
                # Use dependency reference to retrieve object
                dataset = cls.retrieve_dataset(**kwargs.pop('dataset_kwargs', {}))

            # Build dummy object to retrieve hash to look for
            registered_name = kwargs.pop('registered_name')
            new_pipeline = SIMPLEML_REGISTRY.get(registered_name)(name=name, **kwargs)
            new_pipeline.add_dataset(dataset)
            if strict:
                new_pipeline.fit()

            filters = {
                'name': name,
                'registered_name': registered_name,
                'hash_': new_pipeline._hash()
            }

        return BaseProductionPipeline, filters

    @classmethod
    def create_new(cls, registered_name, dataset=None, **kwargs):
        '''
        Stateless method to create a new persistable with the desired parameters
        kwargs are passed directly to persistable

        :param registered_name: Class name registered in SimpleML
        :param dataset: dataset object
        '''
        if dataset is None:
            # Use dependency reference to retrieve object
            dataset = cls.retrieve_dataset(**kwargs.pop('dataset_kwargs', {}))

        new_pipeline = SIMPLEML_REGISTRY.get(registered_name)(**kwargs)
        new_pipeline.add_dataset(dataset)
        new_pipeline.fit()
        new_pipeline.save()

        return new_pipeline

    @classmethod
    def retrieve_dataset(cls, **dataset_kwargs):
        return cls.retrieve_dependency(DatasetCreator, **dataset_kwargs)


class ModelCreator(PersistableCreator):
    @classmethod
    def determine_filters(cls, name='', version=None, strict=False, **kwargs):
        '''
        stateless method to determine which filters to apply when looking for
        existing persistable

        Returns: database class, filter dictionary

        :param registered_name: Class name registered in SimpleML
        :param strict: whether to fit objects first before assuming they are identical
        In theory if all inputs and classes are the same, the outputs should deterministically
        be the same as well (up to random iter). So, you dont need to fit objects
        to be sure they are the same
        '''
        if version is not None:
            filters = {
                'name': name,
                'version': version
            }

        else:
            # Check if dependency object was passed
            pipeline = kwargs.pop('pipeline', None)
            if pipeline is None:
                # Use dependency reference to retrieve object
                pipeline = cls.retrieve_pipeline(**kwargs.pop('pipeline_kwargs', {}))

            # Build dummy object to retrieve hash to look for
            registered_name = kwargs.pop('registered_name')
            new_model = SIMPLEML_REGISTRY.get(registered_name)(name=name, **kwargs)
            new_model.add_pipeline(pipeline)
            if strict:
                new_model.fit()

            filters = {
                'name': name,
                'registered_name': registered_name,
                'hash_': new_model._hash()
            }

        return BaseModel, filters

    @classmethod
    def create_new(cls, registered_name, pipeline=None, **kwargs):
        '''
        Stateless method to create a new persistable with the desired parameters
        kwargs are passed directly to persistable

        :param registered_name: Class name registered in SimpleML
        :param pipeline: pipeline object
        '''
        if pipeline is None:
            # Use dependency reference to retrieve object
            pipeline = cls.retrieve_pipeline(**kwargs.pop('pipeline_kwargs', {}))

        new_model = SIMPLEML_REGISTRY.get(registered_name)(**kwargs)
        new_model.add_pipeline(pipeline)
        new_model.fit()
        new_model.save()

        return new_model

    @classmethod
    def retrieve_pipeline(cls, **pipeline_kwargs):
        return cls.retrieve_dependency(PipelineCreator, **pipeline_kwargs)


class MetricCreator(PersistableCreator):
    @classmethod
    def determine_filters(cls, name=None, model_id=None, strict=False, **kwargs):
        '''
        stateless method to determine which filters to apply when looking for
        existing persistable

        Returns: database class, filter dictionary

        :param registered_name: Class name registered in SimpleML
        :param strict: whether to fit objects first before assuming they are identical
        In theory if all inputs and classes are the same, the outputs should deterministically
        be the same as well (up to random iter). So, you dont need to fit objects
        to be sure they are the same
        '''
        if name is not None and model_id is not None:
            # Can't use default name because metrics are hard coded to reflect dataset split + class
            filters = {
                'name': name,
                'model_id': model_id,
            }

        else:
            # Check if dependency object was passed
            model = kwargs.pop('model', None)
            if model is None:
                # Use dependency reference to retrieve object
                model = cls.retrieve_model(**kwargs.pop('model_kwargs', {}))

            # Build dummy object to retrieve hash to look for
            registered_name = kwargs.pop('registered_name')
            new_metric = SIMPLEML_REGISTRY.get(registered_name)(name=name, **kwargs)
            new_metric.add_model(model)
            if strict:
                new_metric.score()

            filters = {
                'name': new_metric.name,
                'registered_name': registered_name,
                'hash_': new_metric._hash()
            }

        return BaseMetric, filters

    @classmethod
    def create_new(cls, registered_name, model=None, **kwargs):
        '''
        Stateless method to create a new persistable with the desired parameters
        kwargs are passed directly to persistable

        :param registered_name: Class name registered in SimpleML
        :param model: model class
        '''
        if model is None:
            # Use dependency reference to retrieve object
            model = cls.retrieve_model(**kwargs.pop('model_kwargs', {}))

        new_metric = SIMPLEML_REGISTRY.get(registered_name)(**kwargs)
        new_metric.add_model(model)
        new_metric.score()
        new_metric.save()

        return new_metric

    @classmethod
    def retrieve_model(cls, **model_kwargs):
        return cls.retrieve_dependency(ModelCreator, **model_kwargs)
