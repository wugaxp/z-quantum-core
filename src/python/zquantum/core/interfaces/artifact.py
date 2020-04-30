from abc import ABC, abstractmethod
from typing import TextIO
from marshmallow import Schema, fields
import json


class SerializableArtifact(ABC):
    """
    Base class for implementing Orquestra artifacts
    """
    schema_object = Schema.from_dict({"schema": fields.Str()})

    def __init__(self):
        self.schema = "artifact"
        
    @abstractmethod
    def save_to_json(self, filename:str):
        """
        Saves file to json.

        Args:
            filename (str): Name of the file
        """
        return cls.schema_object.dump(self)

    @classmethod
    def load_from_json(cls, file:TextIO):
        """
        Loads file to json.

        Args:
            file (str or file-like object): the name of the file or a file-like object.
        """
        if isinstance(file, str):
            with open(file, 'r') as f:
                data = json.load(f)
        else:
            data = json.load(file)
        artifact = cls.schema_object(data)
        return artifact
