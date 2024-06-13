import os
import numpy as np
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsRasterLayer
from osgeo import gdal, osr
from scipy.cluster.vq import kmeans2, whiten
from scipy.spatial.distance import cdist
from .classify_dialog import UnsupervisedClassifierDialog
from . import resources_rc  # Ensure this is correct

class UnsupervisedClassifier:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&Unsupervised Classifier')
        self.first_start = None

    def tr(self, message):
        return QCoreApplication.translate('UnsupervisedClassifier', message)

    def initGui(self):
        icon_path = ':/icon.png'  # Ensure this path matches your qrc prefix and filename
        self.add_action(
            icon_path,
            text=self.tr(u'Unsupervised Classifier'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None
    ):
        self.dlg = UnsupervisedClassifierDialog(iface=self.iface, parent=self.iface.mainWindow())
        self.dlg.runButton.clicked.connect(self.run_clustering)

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        
        if add_to_toolbar:
            self.iface.addToolBarIcon(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&Unsupervised Classifier'), action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        self.dlg.show()
        result = self.dlg.exec_()
        if result:
            pass

    def run_clustering(self):
        # Get parameters from the dialog
        input_file = self.dlg.inputFileLineEdit.text()
        output_file = self.dlg.outputFileLineEdit.text()
        clustering_method = self.dlg.algorithmComboBox.currentText()
        num_clusters = self.dlg.numClustersSpinBox.value()
        selected_bands = [i + 1 for i in range(self.dlg.selectedBandsListWidget.count()) if self.dlg.selectedBandsListWidget.item(i).checkState() == Qt.Checked]
        max_iter = self.dlg.maxIterSpinBox.value()
        max_merge = self.dlg.maxMergeDoubleSpinBox.value()
        min_split_std = self.dlg.minSplitStdDoubleSpinBox.value()
        max_std = self.dlg.maxStdDoubleSpinBox.value()
        min_samples = self.dlg.minSamplesSpinBox.value()
        open_in_qgis = self.dlg.openInQgisCheckBox.isChecked()

        sat_dataset = gdal.Open(input_file)
        bands_data = [sat_dataset.GetRasterBand(i).ReadAsArray().astype(float) for i in selected_bands]

        nrows, ncols = bands_data[0].shape
        reshaped_data = np.stack(bands_data, axis=-1).reshape(-1, len(selected_bands))
        reshaped_data = clean_data(reshaped_data)
        
        if clustering_method == 'Kmeans (Best Method)':
            centroids, labels = kmeans2(whiten(reshaped_data), num_clusters, minit='points')
        elif clustering_method == 'ISODATA (Time Taking)':
            centroids, labels = isodata_clustering(whiten(reshaped_data), num_clusters, max_iter, max_merge, min_split_std, max_std, min_samples)
        
        clustered_image = labels.reshape(nrows, ncols).astype(np.uint8)
        
        driver = gdal.GetDriverByName('GTiff')
        out_dataset = driver.Create(output_file, ncols, nrows, 1, gdal.GDT_Byte)
        out_dataset.SetGeoTransform(sat_dataset.GetGeoTransform())
        out_dataset.SetProjection(sat_dataset.GetProjection())
        out_band = out_dataset.GetRasterBand(1)
        out_band.WriteArray(clustered_image)
        out_band.FlushCache()
        out_dataset = None

        if open_in_qgis:
            self.iface.addRasterLayer(output_file, "Clustered Image")

# Clustering algorithms
def clean_data(data):
    return np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

def isodata_clustering(data, num_clusters, max_iter, max_merge, min_split_std, max_std, min_samples):
    centroids, labels = kmeans2(data, num_clusters, iter=max_iter, minit='points')
    for _ in range(max_iter):
        unique_labels = np.unique(labels)
        cluster_stats = []
        for label in unique_labels:
            cluster_points = data[labels == label]
            if len(cluster_points) >= min_samples:
                cluster_stats.append((label, np.mean(cluster_points, axis=0), np.std(cluster_points, axis=0)))
        new_centroids = []
        merged = set()
        for i, (label1, mean1, std1) in enumerate(cluster_stats):
            if label1 in merged:
                continue
            for j, (label2, mean2, std2) in enumerate(cluster_stats):
                if label1 != label2 and label2 not in merged:
                    distance = np.linalg.norm(mean1 - mean2)
                    if distance < max_merge:
                        new_mean = (mean1 + mean2) / 2
                        new_centroids.append(new_mean)
                        merged.add(label1)
                        merged.add(label2)
                        break
            else:
                new_centroids.append(mean1)
        final_centroids = []
        for mean in new_centroids:
            if np.any(np.std(data[labels == mean], axis=0) > max_std):
                final_centroids.append(mean + std1 / 2)
                final_centroids.append(mean - std1 / 2)
            else:
                final_centroids.append(mean)
        centroids = np.array(final_centroids)
        distances = cdist(data, centroids, metric='euclidean')
        labels = np.argmin(distances, axis=1)
        if len(final_centroids) >= num_clusters:
            break
    return centroids, labels

# import os
# import numpy as np
# from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
# from qgis.PyQt.QtGui import QIcon
# from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
# from qgis.core import QgsProject, QgsRasterLayer
# from osgeo import gdal, osr
# from .classify_dialog import UnsupervisedClassifierDialog
# from .resources import *

# class UnsupervisedClassifier:
#     def __init__(self, iface):
#         self.iface = iface
#         self.plugin_dir = os.path.dirname(__file__)
#         self.actions = []
#         self.menu = self.tr(u'&Unsupervised Classifier')
#         self.first_start = None

#     def tr(self, message):
#         return QCoreApplication.translate('UnsupervisedClassifier', message)

#     def initGui(self):
#         icon_path = ':/UnsupervisedClassifier/icon.png'
#         self.add_action(
#             icon_path,
#             text=self.tr(u'Unsupervised Classifier'),
#             callback=self.run,
#             parent=self.iface.mainWindow()
#         )

#     def add_action(
#         self,
#         icon_path,
#         text,
#         callback,
#         enabled_flag=True,
#         add_to_menu=True,
#         add_to_toolbar=True,
#         status_tip=None,
#         whats_this=None,
#         parent=None
#     ):
#         self.dlg = UnsupervisedClassifierDialog()
#         self.dlg.runButton.clicked.connect(self.run_clustering)

#         icon = QIcon(icon_path)
#         action = QAction(icon, text, parent)
#         action.triggered.connect(callback)
#         action.setEnabled(enabled_flag)
        
#         if add_to_toolbar:
#             self.iface.addToolBarIcon(action)
#         if add_to_menu:
#             self.iface.addPluginToMenu(self.menu, action)
#         self.actions.append(action)
#         return action

#     def unload(self):
#         for action in self.actions:
#             self.iface.removePluginMenu(self.tr(u'&Unsupervised Classifier'), action)
#             self.iface.removeToolBarIcon(action)

#     def run(self):
#         self.dlg.show()
#         result = self.dlg.exec_()
#         if result:
#             pass

#     def run_clustering(self):
#         # Get parameters from the dialog
#         clustering_method = self.dlg.algorithmComboBox.currentText()
#         num_clusters = self.dlg.numClustersSpinBox.value()
#         selected_bands = [int(self.dlg.selectedBandsListWidget.item(i).text()) for i in range(self.dlg.selectedBandsListWidget.count()) if self.dlg.selectedBandsListWidget.item(i).checkState() == Qt.Checked]
#         max_iter = self.dlg.maxIterSpinBox.value()
#         max_merge = self.dlg.maxMergeDoubleSpinBox.value()
#         min_split_std = self.dlg.minSplitStdDoubleSpinBox.value()
#         max_std = self.dlg.maxStdDoubleSpinBox.value()
#         min_samples = self.dlg.minSamplesSpinBox.value()

#         raster_layer = self.iface.activeLayer()
#         if not isinstance(raster_layer, QgsRasterLayer):
#             QMessageBox.critical(self.dlg, "Error", "Please select a raster layer.")
#             return
        
#         sat_image_path = raster_layer.source()
#         sat_dataset = gdal.Open(sat_image_path)
#         bands_data = [sat_dataset.GetRasterBand(i).ReadAsArray().astype(float) for i in selected_bands]

#         nrows, ncols = bands_data[0].shape
#         reshaped_data = np.stack(bands_data, axis=-1).reshape(-1, len(selected_bands))
#         reshaped_data = clean_data(reshaped_data)
        
#         if clustering_method == 'Kmeans (Best Method)':
#             centroids, labels = kmeans2(whiten(reshaped_data), num_clusters, minit='points')
#         elif clustering_method == 'ISODATA (Time Taking)':
#             centroids, labels = isodata_clustering(whiten(reshaped_data), num_clusters, max_iter, max_merge, min_split_std, max_std, min_samples)
        
#         clustered_image = labels.reshape(nrows, ncols).astype(np.uint8)
#         output_path = QFileDialog.getSaveFileName(self.dlg, "Save Clustered Image", "", "GeoTIFF Files (*.tif)")[0]
        
#         if output_path:
#             driver = gdal.GetDriverByName('GTiff')
#             out_dataset = driver.Create(output_path, ncols, nrows, 1, gdal.GDT_Byte)
#             out_dataset.SetGeoTransform(sat_dataset.GetGeoTransform())
#             out_dataset.SetProjection(sat_dataset.GetProjection())
#             out_band = out_dataset.GetRasterBand(1)
#             out_band.WriteArray(clustered_image)
#             out_band.FlushCache()
#             out_dataset = None
#             self.iface.addRasterLayer(output_path, "Clustered Image")

# # Clustering algorithms
# def clean_data(data):
#     return np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

# def isodata_clustering(data, num_clusters, max_iter, max_merge, min_split_std, max_std, min_samples):
#     centroids, labels = kmeans2(data, num_clusters, iter=max_iter, minit='points')
#     for _ in range(max_iter):
#         unique_labels = np.unique(labels)
#         cluster_stats = []
#         for label in unique_labels:
#             cluster_points = data[labels == label]
#             if len(cluster_points) >= min_samples:
#                 cluster_stats.append((label, np.mean(cluster_points, axis=0), np.std(cluster_points, axis=0)))
#         new_centroids = []
#         merged = set()
#         for i, (label1, mean1, std1) in enumerate(cluster_stats):
#             if label1 in merged:
#                 continue
#             for j, (label2, mean2, std2) in enumerate(cluster_stats):
#                 if label1 != label2 and label2 not in merged:
#                     distance = np.linalg.norm(mean1 - mean2)
#                     if distance < max_merge:
#                         new_mean = (mean1 + mean2) / 2
#                         new_centroids.append(new_mean)
#                         merged.add(label1)
#                         merged.add(label2)
#                         break
#             else:
#                 new_centroids.append(mean1)
#         final_centroids = []
#         for mean in new_centroids:
#             if np.any(np.std(data[labels == mean], axis=0) > max_std):
#                 final_centroids.append(mean + std1 / 2)
#                 final_centroids.append(mean - std1 / 2)
#             else:
#                 final_centroids.append(mean)
#         centroids = np.array(final_centroids)
#         distances = cdist(data, centroids, metric='euclidean')
#         labels = np.argmin(distances, axis=1)
#         if len(final_centroids) >= num_clusters:
#             break
#     return centroids, labels

# import os
# import numpy as np
# from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
# from qgis.PyQt.QtGui import QIcon
# from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
# from qgis.core import QgsProject, QgsRasterLayer
# from osgeo import gdal, osr
# from .classify_dialog import UnsupervisedClassifierDialog
# from .resources import *

# class UnsupervisedClassifier:
#     def __init__(self, iface):
#         self.iface = iface
#         self.plugin_dir = os.path.dirname(__file__)
#         self.actions = []
#         self.menu = self.tr(u'&Unsupervised Classifier')
#         self.first_start = None

#     def tr(self, message):
#         return QCoreApplication.translate('MyClusteringPlugin', message)

#     def initGui(self):
#         icon_path = ':icon.png'
#         self.add_action(
#             icon_path,
#             text=self.tr(u'Unsupervised Classifier'),
#             callback=self.run,
#             parent=self.iface.mainWindow()
#         )

#     def add_action(
#         self,
#         icon_path,
#         text,
#         callback,
#         enabled_flag=True,
#         add_to_menu=True,
#         add_to_toolbar=True,
#         status_tip=None,
#         whats_this=None,
#         parent=None
#     ):
#         self.dlg = UnsupervisedClassifierDialog()
#         self.dlg.runButton.clicked.connect(self.run_clustering)

#         icon = QIcon(icon_path)
#         action = QAction(icon, text, parent)
#         action.triggered.connect(callback)
#         action.setEnabled(enabled_flag)
        
#         if add_to_toolbar:
#             self.iface.addToolBarIcon(action)
#         if add_to_menu:
#             self.iface.addPluginToMenu(self.menu, action)
#         self.actions.append(action)
#         return action

#     def unload(self):
#         for action in self.actions:
#             self.iface.removePluginMenu(self.tr(u'&Unsupervised Classifier'), action)
#             self.iface.removeToolBarIcon(action)

#     def run(self):
#         self.dlg.show()
#         result = self.dlg.exec_()
#         if result:
#             pass

#     def run_clustering(self):
#         # Get parameters from the dialog
#         clustering_method = self.dlg.algorithmComboBox.currentText()
#         num_clusters = self.dlg.numClustersSpinBox.value()
#         selected_bands = [int(self.dlg.selectedBandsListWidget.item(i).text()) for i in range(self.dlg.selectedBandsListWidget.count()) if self.dlg.selectedBandsListWidget.item(i).checkState()]
#         max_iter = self.dlg.maxIterSpinBox.value()
#         max_merge = self.dlg.maxMergeDoubleSpinBox.value()
#         min_split_std = self.dlg.minSplitStdDoubleSpinBox.value()
#         max_std = self.dlg.maxStdDoubleSpinBox.value()
#         min_samples = self.dlg.minSamplesSpinBox.value()

#         raster_layer = self.iface.activeLayer()
#         if not isinstance(raster_layer, QgsRasterLayer):
#             QMessageBox.critical(self.dlg, "Error", "Please select a raster layer.")
#             return
        
#         sat_image_path = raster_layer.source()
#         sat_dataset = gdal.Open(sat_image_path)
#         bands_data = [sat_dataset.GetRasterBand(i).ReadAsArray().astype(float) for i in selected_bands]

#         nrows, ncols = bands_data[0].shape
#         reshaped_data = np.stack(bands_data, axis=-1).reshape(-1, len(selected_bands))
#         reshaped_data = clean_data(reshaped_data)
        
#         if clustering_method == 'Kmeans (Best Method)':
#             centroids, labels = kmeans2(whiten(reshaped_data), num_clusters, minit='points')
#         elif clustering_method == 'ISODATA (Time Taking)':
#             centroids, labels = isodata_clustering(whiten(reshaped_data), num_clusters, max_iter, max_merge, min_split_std, max_std, min_samples)
        
#         clustered_image = labels.reshape(nrows, ncols).astype(np.uint8)
#         output_path = QFileDialog.getSaveFileName(self.dlg, "Save Clustered Image", "", "GeoTIFF Files (*.tif)")[0]
        
#         if output_path:
#             driver = gdal.GetDriverByName('GTiff')
#             out_dataset = driver.Create(output_path, ncols, nrows, 1, gdal.GDT_Byte)
#             out_dataset.SetGeoTransform(sat_dataset.GetGeoTransform())
#             out_dataset.SetProjection(sat_dataset.GetProjection())
#             out_band = out_dataset.GetRasterBand(1)
#             out_band.WriteArray(clustered_image)
#             out_band.FlushCache()
#             out_dataset = None
#             self.iface.addRasterLayer(output_path, "Clustered Image")

# # Clustering algorithms
# def clean_data(data):
#     return np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

# def isodata_clustering(data, num_clusters, max_iter, max_merge, min_split_std, max_std, min_samples):
#     centroids, labels = kmeans2(data, num_clusters, iter=max_iter, minit='points')
#     for _ in range(max_iter):
#         unique_labels = np.unique(labels)
#         cluster_stats = []
#         for label in unique_labels:
#             cluster_points = data[labels == label]
#             if len(cluster_points) >= min_samples:
#                 cluster_stats.append((label, np.mean(cluster_points, axis=0), np.std(cluster_points, axis=0)))
#         new_centroids = []
#         merged = set()
#         for i, (label1, mean1, std1) in enumerate(cluster_stats):
#             if label1 in merged:
#                 continue
#             for j, (label2, mean2, std2) in enumerate(cluster_stats):
#                 if label1 != label2 and label2 not in merged:
#                     distance = np.linalg.norm(mean1 - mean2)
#                     if distance < max_merge:
#                         new_mean = (mean1 + mean2) / 2
#                         new_centroids.append(new_mean)
#                         merged.add(label1)
#                         merged.add(label2)
#                         break
#             else:
#                 new_centroids.append(mean1)
#         final_centroids = []
#         for mean in new_centroids:
#             if np.any(np.std(data[labels == mean], axis=0) > max_std):
#                 final_centroids.append(mean + std1 / 2)
#                 final_centroids.append(mean - std1 / 2)
#             else:
#                 final_centroids.append(mean)
#         centroids = np.array(final_centroids)
#         distances = cdist(data, centroids, metric='euclidean')
#         labels = np.argmin(distances, axis=1)
#         if len(final_centroids) >= num_clusters:
#             break
#     return centroids, labels

# ----------------------------------------------------------------------------------------------------------------------

    # def __init__(self, iface):
    #     self.iface = iface
    #     self.plugin_dir = os.path.dirname(__file__)
    #     self.actions = []
    #     self.menu = self.tr('&Unsupervised Classifier')
    #     self.toolbar = self.iface.addToolBar('UnsupervisedClassifier')
    #     self.toolbar.setObjectName('UnsupervisedClassifier')

    # def tr(self, message):
    #     return QCoreApplication.translate('UnsupervisedClassifier', message)

    # def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True, status_tip=None, parent=None):
    #     icon = QIcon(icon_path)
    #     action = QAction(icon, text, parent)
    #     action.triggered.connect(callback)
    #     action.setEnabled(enabled_flag)
    #     if status_tip:
    #         action.setStatusTip(status_tip)
    #     if add_to_toolbar:
    #         self.toolbar.addAction(action)
    #     if add_to_menu:
    #         self.iface.addPluginToMenu(self.menu, action)
    #     self.actions.append(action)
    #     return action

    # def initGui(self):
    #     icon_path = ':/icon.png'
    #     self.add_action(icon_path, text=self.tr('Unsupervised Classifier'), callback=self.run, parent=self.iface.mainWindow())

    # def unload(self):
    #     for action in self.actions:
    #         self.iface.removePluginMenu(self.tr('&Unsupervised Classifier'), action)
    #         self.iface.removeToolBarIcon(action)
    #     del self.toolbar

    # def run(self):
    #     dlg = UnsupervisedClassifierDialog(self.iface)
    #     dlg.exec_()
