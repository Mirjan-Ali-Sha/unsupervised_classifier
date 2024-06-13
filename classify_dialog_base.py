# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'classify_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ClassifyDialogBase(object):
    def setupUi(self, ClassifyDialogBase):
        ClassifyDialogBase.setObjectName("ClassifyDialogBase")
        ClassifyDialogBase.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(ClassifyDialogBase)
        self.verticalLayout.setObjectName("verticalLayout")
        self.algorithmComboBox = QtWidgets.QComboBox(ClassifyDialogBase)
        self.algorithmComboBox.setObjectName("algorithmComboBox")
        self.verticalLayout.addWidget(self.algorithmComboBox)
        self.numClustersSpinBox = QtWidgets.QSpinBox(ClassifyDialogBase)
        self.numClustersSpinBox.setMinimum(2)
        self.numClustersSpinBox.setMaximum(10)
        self.numClustersSpinBox.setProperty("value", 5)
        self.numClustersSpinBox.setObjectName("numClustersSpinBox")
        self.verticalLayout.addWidget(self.numClustersSpinBox)
        self.isodataOptionsGroupBox = QtWidgets.QGroupBox(ClassifyDialogBase)
        self.isodataOptionsGroupBox.setObjectName("isodataOptionsGroupBox")
        self.formLayout = QtWidgets.QFormLayout(self.isodataOptionsGroupBox)
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(self.isodataOptionsGroupBox)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.maxIterSpinBox = QtWidgets.QSpinBox(self.isodataOptionsGroupBox)
        self.maxIterSpinBox.setMaximum(1000)
        self.maxIterSpinBox.setProperty("value", 100)
        self.maxIterSpinBox.setObjectName("maxIterSpinBox")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.maxIterSpinBox)
        self.label_2 = QtWidgets.QLabel(self.isodataOptionsGroupBox)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.maxMergeDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.isodataOptionsGroupBox)
