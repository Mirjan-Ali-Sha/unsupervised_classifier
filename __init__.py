# -*- coding: utf-8 -*-
# noinspection PyPep8Naming
def classFactory(iface):
    from .classify import UnsupervisedClassifier
    return UnsupervisedClassifier(iface)