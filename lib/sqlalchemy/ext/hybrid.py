# ext/hybrid.py
# Copyright (C) 2005-2011 the SQLAlchemy authors and contributors <see AUTHORS file>
#
# This module is part of SQLAlchemy and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

"""Define attributes on ORM-mapped classes that have 'hybrid' behavior.

'hybrid' means the attribute has distinct behaviors defined at the
class level and at the instance level.

Consider a table `interval` as below::

    from sqlalchemy import MetaData, Table, Column, Integer
    from sqlalchemy.orm import mapper, create_session

    engine = create_engine('sqlite://')
    metadata = MetaData()

    interval_table = Table('interval', metadata,
        Column('id', Integer, primary_key=True),
        Column('start', Integer, nullable=False),
        Column('end', Integer, nullable=False))
    metadata.create_all(engine)

We can define higher level functions on mapped classes that produce SQL
expressions at the class level, and Python expression evaluation at the
instance level.  Below, each function decorated with :func:`hybrid.method`
or :func:`hybrid.property` may receive ``self`` as an instance of the class,
or as the class itself::

    # A base class for intervals

    from sqlalchemy.orm.hybrid import hybrid_property, hybrid_method

    class Interval(object):
        def __init__(self, start, end):
            self.start = start
            self.end = end

        @hybrid_property
        def length(self):
            return self.end - self.start

        @hybrid_method
        def contains(self,point):
            return (self.start <= point) & (point < self.end)

        @hybrid_method
        def intersects(self, other):
            return self.contains(other.start) | self.contains(other.end)



"""
from sqlalchemy import util
from sqlalchemy.orm import attributes, interfaces

class hybrid_method(object):
    def __init__(self, func, expr=None):
        self.func = func
        self.expr = expr or func

    def __get__(self, instance, owner):
        if instance is None:
            return new.instancemethod(self.expr, owner, owner.__class__)
        else:
            return new.instancemethod(self.func, instance, owner)

    def expression(self, expr):
        self.expr = expr
        return self

class hybrid_property(object):
    def __init__(self, fget, fset=None, fdel=None, expr=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.expr = expr or fget
        util.update_wrapper(self, fget)

    def __get__(self, instance, owner):
        if instance is None:
            return self.expr(owner)
        else:
            return self.fget(instance)

    def __set__(self, instance, value):
        self.fset(instance, value)

    def __delete__(self, instance):
        self.fdel(instance)

    def setter(self, fset):
        self.fset = fset
        return self

    def deleter(self, fdel):
        self.fdel = fdel
        return self

    def expression(self, expr):
        self.expr = expr
        return self

    def comparator(self, comparator):
        proxy_attr = attributes.\
                        create_proxied_attribute(self)
        def expr(owner):
            return proxy_attr(owner, self.__name__, self, comparator(owner))
        self.expr = expr
        return self


class Comparator(interfaces.PropComparator):
    def __init__(self, expression):
        self.expression = expression

    def __clause_element__(self):
        expr = self.expression
        while hasattr(expr, '__clause_element__'):
            expr = expr.__clause_element__()
        return expr

    def adapted(self, adapter):
        # interesting....
        return self


