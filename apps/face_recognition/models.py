# -*- encoding: utf-8 -*-
"""
Copyright (c) 2022 - VKIST
"""

from enum import unique
from apps import db
import datetime

class Images(db.Model):

    __tablename__ = 'Images'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    person_id = db.Column(db.Integer)
    image_id = db.Column(db.String(64), unique=True)
    embedding = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)


class DefineImages(db.Model):

    __tablename__ = 'DefineImages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    person_id = db.Column(db.Integer)
    embedding_id = db.Column(db.Integer, unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)


class People(db.Model):

    __tablename__ = 'People'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    access_key = db.Column(db.String(64), unique=True)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)


class FullImages(db.Model):

    __tablename__ = 'FullImages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    image_id = db.Column(db.Integer)
    full_image_id = db.Column(db.String(64))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            setattr(self, property, value)

    def __repr__(self):
        return str(self.id)