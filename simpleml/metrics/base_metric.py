from simpleml.persistables.base_persistable import BasePersistable, GUID
from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

__author__ = 'Elisha Yadgaran'


class BaseMetric(BasePersistable):
    '''
    Base class for all Metric objects

    -------
    Schema
    -------
    name: the metric name
    values: JSON object with key: value pairs for performance on test dataset
        (ex: FPR: TPR to create ROC Curve)
        Singular value metrics take the form - {'agg': value}
    model_id: foreign key to the model that was used to generate predictions

    TODO: Should join criteria be composite of model and dataset for multiple
        duplicate metric objects computed over different test datasets?
    '''
    __tablename__ = 'metrics'

    values = Column(JSONB, nullable=False)

    # Only dependency is the model (to score in production)
    model_id = Column(GUID, ForeignKey("models.id"))
    model = relationship('BaseModel')

    __table_args__ = (
        # Unique constraint for versioning
        UniqueConstraint('name', 'version', name='metric_name_version_unique'),
        # Index for searching through friendly names
        Index('metric_name_index', 'name'),
     )
