# from qgis.PyQt.QtWidgets import QDialog
# from .classify_dialog_base import Ui_ClassifyDialogBase
# from PyQt5 import QtWidgets, uic
# from PyQt5.QtCore import Qt
# import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QComboBox, QSpinBox, QGroupBox, QFormLayout, QLabel, QDoubleSpinBox, QListWidget, QPushButton, QListWidgetItem, QLineEdit, QFileDialog, QCheckBox, QHBoxLayout
from PyQt5.QtCore import Qt
from osgeo import gdal
import os
from qgis.core import QgsRasterLayer

class UnsupervisedClassifierDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Unsupervised Classifier")
        self.setGeometry(100, 100, 600, 400)  # Set the window wider
        self.setWindowModality(Qt.ApplicationModal)  # Keep the dialog on top until it is closed

        self.layout = QVBoxLayout(self)

        # Input selection
        self.inputFileLabel = QLabel("Select Input", self)
        self.inputFileLineEdit = QLineEdit(self)
        self.inputFileButton = QPushButton("...", self)
        self.inputFileButton.clicked.connect(self.select_input_file)
        self.inputFileLayout = QHBoxLayout()
        self.inputFileLayout.addWidget(self.inputFileLineEdit)
        self.inputFileLayout.addWidget(self.inputFileButton)
        self.layout.addWidget(self.inputFileLabel)
        self.layout.addLayout(self.inputFileLayout)

        # Output selection
        self.outputFileLabel = QLabel("Select Output", self)
        self.outputFileLineEdit = QLineEdit(self)
        self.outputFileButton = QPushButton("...", self)
        self.outputFileButton.clicked.connect(self.select_output_file)
        self.outputFileLayout = QHBoxLayout()
        self.outputFileLayout.addWidget(self.outputFileLineEdit)
        self.outputFileLayout.addWidget(self.outputFileButton)
        self.layout.addWidget(self.outputFileLabel)
        self.layout.addLayout(self.outputFileLayout)

        # Algorithm selection
        self.algorithmLabel = QLabel("Select Clustering Method:", self)
        self.layout.addWidget(self.algorithmLabel)
        self.algorithmComboBox = QComboBox(self)
        self.algorithmComboBox.addItem("Kmeans (Best & Fast Method)")
        self.algorithmComboBox.addItem("ISODATA (Complex & Time Taking)")
        self.layout.addWidget(self.algorithmComboBox)

        # Number of clusters
        self.numClustersSpinBox = QSpinBox(self)
        self.numClustersSpinBox.setMinimum(2)
        self.numClustersSpinBox.setMaximum(10)
        self.numClustersSpinBox.setValue(5)
        self.numClustersSpinBox.setPrefix("Number of Clusters: ")
        self.layout.addWidget(self.numClustersSpinBox)

        # ISODATA options
        self.isodataOptionsGroupBox = QGroupBox("ISODATA Options", self)
        self.isodataOptionsLayout = QFormLayout(self.isodataOptionsGroupBox)
        
        self.maxIterLabel = QLabel("Max Iterations", self)
        self.maxIterSpinBox = QSpinBox(self)
        self.maxIterSpinBox.setMaximum(1000)
        self.maxIterSpinBox.setValue(100)
        self.isodataOptionsLayout.addRow(self.maxIterLabel, self.maxIterSpinBox)
        
        self.maxMergeLabel = QLabel("Max Merge", self)
        self.maxMergeDoubleSpinBox = QDoubleSpinBox(self)
        self.maxMergeDoubleSpinBox.setMaximum(10.0)
        self.maxMergeDoubleSpinBox.setValue(0.5)
        self.isodataOptionsLayout.addRow(self.maxMergeLabel, self.maxMergeDoubleSpinBox)
        
        self.minSplitStdLabel = QLabel("Min Split Std", self)
        self.minSplitStdDoubleSpinBox = QDoubleSpinBox(self)
        self.minSplitStdDoubleSpinBox.setMaximum(10.0)
        self.minSplitStdDoubleSpinBox.setValue(0.5)
        self.isodataOptionsLayout.addRow(self.minSplitStdLabel, self.minSplitStdDoubleSpinBox)
        
        self.maxStdLabel = QLabel("Max Std", self)
        self.maxStdDoubleSpinBox = QDoubleSpinBox(self)
        self.maxStdDoubleSpinBox.setMaximum(10.0)
        self.maxStdDoubleSpinBox.setValue(1.0)
        self.isodataOptionsLayout.addRow(self.maxStdLabel, self.maxStdDoubleSpinBox)
        
        self.minSamplesLabel = QLabel("Min Samples", self)
        self.minSamplesSpinBox = QSpinBox(self)
        self.minSamplesSpinBox.setMaximum(1000)
        self.minSamplesSpinBox.setValue(10)
        self.isodataOptionsLayout.addRow(self.minSamplesLabel, self.minSamplesSpinBox)
        
        self.layout.addWidget(self.isodataOptionsGroupBox)

        # Band selection options
        self.useNumBandsCheckBox = QCheckBox("Do you want to select available bands?", self)
        self.layout.addWidget(self.useNumBandsCheckBox)

        self.numBandsSpinBox = QSpinBox(self)
        self.numBandsSpinBox.setMinimum(1)
        self.numBandsSpinBox.setMaximum(10)
        self.numBandsSpinBox.setValue(4)
        self.numBandsSpinBox.setPrefix("Number of Bands: ")
        self.layout.addWidget(self.numBandsSpinBox)

        self.selectedBandsListWidget = QListWidget(self)
        self.layout.addWidget(self.selectedBandsListWidget)

        # Open output in QGIS
        self.openInQgisCheckBox = QCheckBox("Open the output in QGIS", self)
        self.layout.addWidget(self.openInQgisCheckBox)

        # Run button
        self.runButton = QPushButton("Run Clustering", self)
        self.layout.addWidget(self.runButton)
        
        # Connect signals for enabling/disabling options based on selected algorithm
        self.algorithmComboBox.currentIndexChanged.connect(self.toggle_options)
        self.useNumBandsCheckBox.stateChanged.connect(self.toggle_band_selection)
        self.numBandsSpinBox.valueChanged.connect(self.populate_band_options)
        self.inputFileLineEdit.textChanged.connect(self.update_band_options)
        
        # Initial setup
        self.toggle_options()
        self.toggle_band_selection()
        self.populate_band_options()
        self.isodataOptionsGroupBox.hide()  # Hide ISODATA options by default

    def showEvent(self, event):
        # Reset all values when the dialog is shown
        self.reset_values()
        super().showEvent(event)

    def reset_values(self):
        self.inputFileLineEdit.clear()
        self.outputFileLineEdit.clear()
        self.algorithmComboBox.setCurrentIndex(0)
        self.numClustersSpinBox.setValue(5)
        self.maxIterSpinBox.setValue(100)
        self.maxMergeDoubleSpinBox.setValue(0.5)
        self.minSplitStdDoubleSpinBox.setValue(0.5)
        self.maxStdDoubleSpinBox.setValue(1.0)
        self.minSamplesSpinBox.setValue(10)
        self.useNumBandsCheckBox.setChecked(False)
        self.numBandsSpinBox.setValue(4)
        self.selectedBandsListWidget.clear()
        self.openInQgisCheckBox.setChecked(False)
        self.isodataOptionsGroupBox.hide()
        self.toggle_band_selection()
        self.adjustSize()

    def toggle_options(self):
        if self.algorithmComboBox.currentText() == "ISODATA (Complex & Time Taking)":
            self.isodataOptionsGroupBox.show()
        else:
            self.isodataOptionsGroupBox.hide()
        self.adjustSize()

    def toggle_band_selection(self):
        if self.useNumBandsCheckBox.isChecked():
            self.numBandsSpinBox.hide()
            self.selectedBandsListWidget.show()
        else:
            self.numBandsSpinBox.show()
            self.selectedBandsListWidget.hide()
        self.adjustSize()

    def populate_band_options(self):
        self.selectedBandsListWidget.clear()
        for i in range(1, self.numBandsSpinBox.value() + 1):
            item = QListWidgetItem(f"Band {i}")
            item.setCheckState(Qt.Checked)
            self.selectedBandsListWidget.addItem(item)

    def select_input_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Input File", "", "GeoTIFF Files (*.tif)")
        if filename:
            self.inputFileLineEdit.setText(filename)
            self.update_band_options()

    def update_band_options(self):
        input_file = self.inputFileLineEdit.text()
        if input_file:
            dataset = gdal.Open(input_file)
            if dataset:
                self.selectedBandsListWidget.clear()
                num_bands = dataset.RasterCount
                self.numBandsSpinBox.setMaximum(num_bands)
                self.numBandsSpinBox.setValue(num_bands)
                for i in range(1, num_bands + 1):
                    band = dataset.GetRasterBand(i)
                    description = band.GetDescription() or f"Band {i}"
                    item = QListWidgetItem(description)
                    item.setCheckState(Qt.Checked)
                    self.selectedBandsListWidget.addItem(item)

    def select_output_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Output File", "", "GeoTIFF Files (*.tif)")
        if filename:
            self.outputFileLineEdit.setText(filename)

# from PyQt5.QtWidgets import QDialog, QVBoxLayout, QComboBox, QSpinBox, QGroupBox, QFormLayout, QLabel, QDoubleSpinBox, QListWidget, QPushButton, QListWidgetItem

# class UnsupervisedClassifierDialog(QDialog):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Unsupervised Classifier")
#         self.setGeometry(100, 100, 400, 300)
        
#         self.layout = QVBoxLayout(self)
        
#         self.algorithmComboBox = QComboBox(self)
#         self.algorithmComboBox.addItem("Kmeans (Best & Fast Method)")
#         self.algorithmComboBox.addItem("ISODATA (Complex & Time Taking)")
#         self.layout.addWidget(self.algorithmComboBox)
        
#         self.numClustersSpinBox = QSpinBox(self)
#         self.numClustersSpinBox.setMinimum(2)
#         self.numClustersSpinBox.setMaximum(10)
#         self.numClustersSpinBox.setValue(5)
#         self.numClustersSpinBox.setPrefix("Number of Clusters: ")
#         self.layout.addWidget(self.numClustersSpinBox)
        
#         self.isodataOptionsGroupBox = QGroupBox("ISODATA Options", self)
#         self.isodataOptionsLayout = QFormLayout(self.isodataOptionsGroupBox)
        
#         self.maxIterLabel = QLabel("Max Iterations", self)
#         self.maxIterSpinBox = QSpinBox(self)
#         self.maxIterSpinBox.setMaximum(1000)
#         self.maxIterSpinBox.setValue(100)
#         self.isodataOptionsLayout.addRow(self.maxIterLabel, self.maxIterSpinBox)
        
#         self.maxMergeLabel = QLabel("Max Merge", self)
#         self.maxMergeDoubleSpinBox = QDoubleSpinBox(self)
#         self.maxMergeDoubleSpinBox.setMaximum(10.0)
#         self.maxMergeDoubleSpinBox.setValue(0.5)
#         self.isodataOptionsLayout.addRow(self.maxMergeLabel, self.maxMergeDoubleSpinBox)
        
#         self.minSplitStdLabel = QLabel("Min Split Std", self)
#         self.minSplitStdDoubleSpinBox = QDoubleSpinBox(self)
#         self.minSplitStdDoubleSpinBox.setMaximum(10.0)
#         self.minSplitStdDoubleSpinBox.setValue(0.5)
#         self.isodataOptionsLayout.addRow(self.minSplitStdLabel, self.minSplitStdDoubleSpinBox)
        
#         self.maxStdLabel = QLabel("Max Std", self)
#         self.maxStdDoubleSpinBox = QDoubleSpinBox(self)
#         self.maxStdDoubleSpinBox.setMaximum(10.0)
#         self.maxStdDoubleSpinBox.setValue(1.0)
#         self.isodataOptionsLayout.addRow(self.maxStdLabel, self.maxStdDoubleSpinBox)
        
#         self.minSamplesLabel = QLabel("Min Samples", self)
#         self.minSamplesSpinBox = QSpinBox(self)
#         self.minSamplesSpinBox.setMaximum(1000)
#         self.minSamplesSpinBox.setValue(10)
#         self.isodataOptionsLayout.addRow(self.minSamplesLabel, self.minSamplesSpinBox)
        
#         self.layout.addWidget(self.isodataOptionsGroupBox)
        
#         self.numBandsSpinBox = QSpinBox(self)
#         self.numBandsSpinBox.setMinimum(1)
#         self.numBandsSpinBox.setMaximum(10)
#         self.numBandsSpinBox.setValue(4)
#         self.numBandsSpinBox.setPrefix("Number of Bands: ")
#         self.layout.addWidget(self.numBandsSpinBox)
        
#         self.selectedBandsListWidget = QListWidget(self)
#         self.layout.addWidget(self.selectedBandsListWidget)
        
#         self.runButton = QPushButton("Run Clustering", self)
#         self.layout.addWidget(self.runButton)
        
#         self.algorithmComboBox.currentIndexChanged.connect(self.toggle_options)
#         self.numBandsSpinBox.valueChanged.connect(self.populate_band_options)
        
#         self.toggle_options()
#         self.populate_band_options()

#     def toggle_options(self):
#         if self.algorithmComboBox.currentText() == "ISODATA (Complex & Time Taking)":
#             self.isodataOptionsGroupBox.setEnabled(True)
#         else:
#             self.isodataOptionsGroupBox.setEnabled(False)

#     def populate_band_options(self):
#         self.selectedBandsListWidget.clear()
#         for i in range(1, self.numBandsSpinBox.value() + 1):
#             item = QListWidgetItem(str(i))
#             item.setCheckState(Qt.Checked)
#             self.selectedBandsListWidget.addItem(item)


# class UnsupervisedClassifierDialog(QDialog, Ui_ClassifyDialogBase):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         uic.loadUi(os.path.join(os.path.dirname(__file__), 'classify_dialog_base.ui'), self)
        
#         # Populate the algorithm combo box
#         self.algorithmComboBox.addItem("Kmeans (Best & Fast Method)")
#         self.algorithmComboBox.addItem("ISODATA (Complex & Time Taking)")
        
#         # Connect signals for enabling/disabling options based on selected algorithm
#         self.algorithmComboBox.currentIndexChanged.connect(self.toggle_options)
#         self.numBandsSpinBox.valueChanged.connect(self.populate_band_options)
        
#         # Initial setup
#         self.toggle_options()
#         self.populate_band_options()

#     def toggle_options(self):
#         if self.algorithmComboBox.currentText() == "ISODATA (Complex & Time Taking)":
#             self.isodataOptionsGroupBox.setEnabled(True)
#         else:
#             self.isodataOptionsGroupBox.setEnabled(False)

#     def populate_band_options(self):
#         self.selectedBandsListWidget.clear()
#         for i in range(1, self.numBandsSpinBox.value() + 1):
#             item = QtWidgets.QListWidgetItem(str(i))
#             item.setCheckState(Qt.Checked)
#             self.selectedBandsListWidget.addItem(item)

# from qgis.PyQt.QtWidgets import QDialog
# from .classify_dialog_base import Ui_ClassifyDialogBase
# # # import numpy as np
# # # import cv2
# from qgis.core import QgsProject
# from PyQt5 import QtWidgets, uic
# from PyQt5.QtCore import Qt
# import os
# class UnsupervisedClassifierDialog(QDialog, Ui_ClassifyDialogBase):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         uic.loadUi(os.path.join(os.path.dirname(__file__), 'classify_dialog_base.ui'), self)
        
#         # Populate the algorithm combo box
#         self.algorithmComboBox.addItem("Kmeans (Best & Fast Method)")
#         self.algorithmComboBox.addItem("ISODATA (Complex & Time Taking)")
        
#         # Connect signals for enabling/disabling options based on selected algorithm
#         self.algorithmComboBox.currentIndexChanged.connect(self.toggle_options)
#         self.numBandsSpinBox.valueChanged.connect(self.populate_band_options)
        
#         # Initial setup
#         self.toggle_options()
#         self.populate_band_options()

#     def toggle_options(self):
#         if self.algorithmComboBox.currentText() == "ISODATA (Complex & Time Taking)":
#             self.isodataOptionsGroupBox.setEnabled(True)
#         else:
#             self.isodataOptionsGroupBox.setEnabled(False)

#     def populate_band_options(self):
#         self.selectedBandsListWidget.clear()
#         for i in range(1, self.numBandsSpinBox.value() + 1):
#             item = QtWidgets.QListWidgetItem(str(i))
#             item.setCheckState(Qt.Checked)
#             self.selectedBandsListWidget.addItem(item)
