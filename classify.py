# -*- coding: utf-8 -*-
import os
import numpy as np
from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox, QToolBar
from qgis.core import QgsProject, QgsRasterLayer
from osgeo import gdal, osr
from .classify_dialog import UnsupervisedClassifierDialog
from . import resources_rc

# Suppress all warnings
import warnings
warnings.filterwarnings('ignore')

# Try to import sklearn (required)
try:
    from sklearn.cluster import AgglomerativeClustering, DBSCAN, SpectralClustering, KMeans
    sklearn_available = True
except ImportError:
    sklearn_available = False
    print("Warning: scikit-learn not available. Please install it.")

# Try to import scipy for distance calculations only
try:
    from scipy.spatial.distance import cdist
    scipy_available = True
except ImportError:
    scipy_available = False
    # Fallback to numpy-based distance calculation
    def cdist(A, B, metric='euclidean'):
        if metric == 'euclidean':
            return np.sqrt(((A[:, np.newaxis, :] - B[np.newaxis, :, :]) ** 2).sum(axis=2))
        else:
            raise ValueError("Only euclidean metric supported in fallback")


class UnsupervisedClassifier:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = self.tr(u'&MAS Raster Processing')
        self.toolbar = None
        self.first_start = None

    def tr(self, message):
        return QCoreApplication.translate('UnsupervisedClassifier', message)

    def initGui(self):
        icon_path = ':/cluster.png'
        self.toolbar = self.iface.mainWindow().findChild(QToolBar, 'MASRasterProcessingToolbar')
        if self.toolbar is None:
            self.toolbar = self.iface.addToolBar(u'MAS Raster Processing')
            self.toolbar.setObjectName('MASRasterProcessingToolbar')

        self.action_UnspvClassification = QAction(QIcon(icon_path), u"&Unsupervised Classifier", self.iface.mainWindow())
        self.action_UnspvClassification.triggered.connect(self.run)
        self.iface.addPluginToRasterMenu(self.menu, self.action_UnspvClassification)
        self.toolbar.addAction(self.action_UnspvClassification)
        self.actions.append(self.action_UnspvClassification)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&MAS Raster Processing'), action)
            self.iface.removeToolBarIcon(action)
        if self.toolbar:
            del self.toolbar

    def run(self):
        if not hasattr(self, 'dlg'):
            self.dlg = UnsupervisedClassifierDialog(iface=self.iface, parent=self.iface.mainWindow())
            self.dlg.runButton.clicked.connect(self.run_clustering)
        self.dlg.show()
        result = self.dlg.exec_()

    def run_clustering(self):
        # Get selected rasters
        selected_rasters = self.dlg.get_selected_rasters()
        
        if not selected_rasters:
            QMessageBox.warning(self.dlg, "Warning", "No rasters selected. Please add and select rasters to process.")
            return
        
        if not sklearn_available:
            QMessageBox.critical(self.dlg, "Error", "scikit-learn is required but not installed. Please install it using: pip install scikit-learn")
            return
        
        self.dlg.runButton.setEnabled(False)
        self.dlg.runButton.setText("Processing...")
        
        clustering_method = self.dlg.algorithmComboBox.currentText()
        num_clusters = self.dlg.numClustersSpinBox.value()
        max_iter = self.dlg.maxIterSpinBox.value()
        max_merge = self.dlg.maxMergeDoubleSpinBox.value()
        min_split_std = self.dlg.minSplitStdDoubleSpinBox.value()
        max_std = self.dlg.maxStdDoubleSpinBox.value()
        min_samples = self.dlg.minSamplesSpinBox.value()
        open_in_qgis = self.dlg.openInQgisCheckBox.isChecked()
        
        total_files = len(selected_rasters)
        self.dlg.update_progress(0, total_files, "Starting batch processing...")
        
        success_count = 0
        failed_files = []
        
        for idx, raster_info in enumerate(selected_rasters, start=1):
            input_file = raster_info['input']
            output_file = raster_info['output']
            selected_bands = raster_info.get('bands', [])  # Get bands from the dict
            file_name = os.path.basename(input_file)
            
            self.dlg.update_progress(idx - 1, total_files, f"Processing ({idx}/{total_files}): {file_name}")
            
            try:
                if not os.path.exists(input_file):
                    failed_files.append(f"{file_name}: File not found")
                    continue
                
                # Check if bands are selected
                if not selected_bands:
                    failed_files.append(f"{file_name}: No bands selected")
                    continue
                
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                success, error_msg = self.process_single_raster(
                    input_file, output_file, clustering_method, num_clusters,
                    selected_bands, max_iter, max_merge, min_split_std,
                    max_std, min_samples, open_in_qgis
                )
                
                if success:
                    success_count += 1
                    self.dlg.update_progress(idx, total_files, f"Completed ({idx}/{total_files}): {file_name}")
                else:
                    failed_files.append(f"{file_name}: {error_msg}")
                    
            except Exception as e:
                failed_files.append(f"{file_name}: {str(e)}")
        
        self.dlg.hide_progress()
        self.dlg.runButton.setEnabled(True)
        self.dlg.runButton.setText("Run Classification")
        
        message = f"Successfully processed {success_count} out of {total_files} raster(s)."
        if failed_files:
            message += f"\n\nFailed files:\n" + "\n".join(failed_files[:10])
            if len(failed_files) > 10:
                message += f"\n... and {len(failed_files) - 10} more"
        
        if success_count > 0:
            QMessageBox.information(self.dlg, "Classification Complete", message)
        else:
            QMessageBox.critical(self.dlg, "Classification Failed", message)

    def process_single_raster(self, input_file, output_file, clustering_method, num_clusters,
                             selected_bands, max_iter, max_merge, min_split_std,
                             max_std, min_samples, open_in_qgis):
        try:
            sat_dataset = gdal.Open(input_file)
            if sat_dataset is None:
                return False, "Could not open file"
            
            actual_band_count = sat_dataset.RasterCount
            valid_bands = [b for b in selected_bands if b <= actual_band_count]
            
            if not valid_bands:
                return False, f"No valid bands (file has {actual_band_count} bands)"
            
            bands_data = [sat_dataset.GetRasterBand(i).ReadAsArray().astype(float) for i in valid_bands]
            
            nrows, ncols = bands_data[0].shape
            reshaped_data = np.stack(bands_data, axis=-1).reshape(-1, len(valid_bands))
            reshaped_data = clean_data(reshaped_data)
            normalized_data = normalize_data(reshaped_data)
            
            try:
                if clustering_method == 'Kmeans (Best Method)':
                    model = KMeans(n_clusters=num_clusters, n_init=10, max_iter=300, random_state=42)
                    labels = model.fit_predict(normalized_data)
                        
                elif clustering_method == 'ISODATA (Time Taking)':
                    labels = isodata_clustering(normalized_data, num_clusters, max_iter, 
                                               max_merge, min_split_std, max_std, min_samples)
                        
                elif clustering_method == 'Agglomerative Clustering':
                    if reshaped_data.shape[0] > 10000:
                        return False, "Dataset too large for Agglomerative Clustering (>10k pixels)"
                    model = AgglomerativeClustering(n_clusters=num_clusters)
                    labels = model.fit_predict(normalized_data)
                    
                elif clustering_method == 'DBSCAN':
                    model = DBSCAN(eps=0.5, min_samples=5)
                    labels = model.fit_predict(normalized_data)
                    unique_labels = np.unique(labels)
                    if len(unique_labels) < 2:
                        return False, "DBSCAN failed to find sufficient clusters"
                    labels = np.where(labels == -1, len(unique_labels), labels)
                    
                elif clustering_method == 'Spectral Clustering':
                    if reshaped_data.shape[0] > 10000:
                        return False, "Dataset too large for Spectral Clustering (>10k pixels)"
                    model = SpectralClustering(n_clusters=num_clusters, random_state=42)
                    labels = model.fit_predict(normalized_data)
                else:
                    return False, f"Unknown clustering method: {clustering_method}"
                    
            except Exception as cluster_error:
                return False, f"Clustering error: {str(cluster_error)}"

            clustered_image = labels.reshape(nrows, ncols).astype(np.uint8)
            
            driver = gdal.GetDriverByName('GTiff')
            out_dataset = driver.Create(output_file, ncols, nrows, 1, gdal.GDT_Byte)
            out_dataset.SetGeoTransform(sat_dataset.GetGeoTransform())
            out_dataset.SetProjection(sat_dataset.GetProjection())
            out_band = out_dataset.GetRasterBand(1)
            out_band.WriteArray(clustered_image)
            out_band.FlushCache()
            out_dataset = None
            sat_dataset = None

            if open_in_qgis:
                layer_name = os.path.splitext(os.path.basename(output_file))[0]
                self.iface.addRasterLayer(output_file, layer_name)

            return True, "Success"

        except Exception as e:
            return False, str(e)


def clean_data(data):
    """Clean data by replacing NaN and infinite values"""
    return np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)


def normalize_data(data):
    """Normalize data using standardization (z-score)"""
    std = np.std(data, axis=0)
    std[std == 0] = 1  # Avoid division by zero
    mean = np.mean(data, axis=0)
    normalized = (data - mean) / std
    return normalized


def isodata_clustering(data, num_clusters, max_iter, max_merge, min_split_std, max_std, min_samples):
    """ISODATA clustering algorithm using sklearn KMeans"""
    try:
        # Initial clustering using KMeans
        model = KMeans(n_clusters=num_clusters, n_init=10, max_iter=max_iter, random_state=42)
        labels = model.fit_predict(data)
        centroids = model.cluster_centers_
        
        # ISODATA iterations
        for iteration in range(min(max_iter // 10, 10)):  # Limit ISODATA iterations
            unique_labels = np.unique(labels)
            cluster_stats = []
            
            for label in unique_labels:
                cluster_points = data[labels == label]
                if len(cluster_points) >= min_samples:
                    cluster_stats.append({
                        'label': label,
                        'mean': np.mean(cluster_points, axis=0),
                        'std': np.std(cluster_points, axis=0),
                        'size': len(cluster_points)
                    })
            
            if not cluster_stats:
                break
            
            # Merge close clusters
            new_centroids = []
            merged = set()
            
            for i, stat1 in enumerate(cluster_stats):
                if stat1['label'] in merged:
                    continue
                
                merged_this = False
                for j, stat2 in enumerate(cluster_stats):
                    if i != j and stat2['label'] not in merged:
                        distance = np.linalg.norm(stat1['mean'] - stat2['mean'])
                        if distance < max_merge:
                            new_mean = (stat1['mean'] + stat2['mean']) / 2
                            new_centroids.append(new_mean)
                            merged.add(stat1['label'])
                            merged.add(stat2['label'])
                            merged_this = True
                            break
                
                if not merged_this:
                    new_centroids.append(stat1['mean'])
            
            # Split clusters with high variance
            final_centroids = []
            for i, mean in enumerate(new_centroids):
                stat = cluster_stats[i] if i < len(cluster_stats) else None
                if stat and np.max(stat['std']) > max_std and stat['size'] > min_samples * 2:
                    # Split into two clusters
                    offset = stat['std'] * 0.5
                    final_centroids.append(mean + offset)
                    final_centroids.append(mean - offset)
                else:
                    final_centroids.append(mean)
            
            if not final_centroids:
                break
            
            # Reassign labels based on new centroids
            centroids = np.array(final_centroids)
            distances = cdist(data, centroids, metric='euclidean')
            labels = np.argmin(distances, axis=1)
            
            # Stop if we have enough clusters
            if len(final_centroids) >= num_clusters:
                break
        
        return labels
        
    except Exception as e:
        print(f"ISODATA error: {str(e)}, falling back to standard KMeans")
        # Fallback to standard KMeans
        model = KMeans(n_clusters=num_clusters, n_init=10, max_iter=max_iter, random_state=42)
        labels = model.fit_predict(data)
        return labels
