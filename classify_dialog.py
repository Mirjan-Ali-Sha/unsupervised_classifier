# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QComboBox, QSpinBox, QGroupBox, 
                             QFormLayout, QLabel, QDoubleSpinBox, QListWidget, QPushButton, 
                             QListWidgetItem, QLineEdit, QFileDialog, QCheckBox, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView, QWidget, QProgressBar)
from PyQt5.QtCore import Qt
from osgeo import gdal
import os
from qgis.core import QgsProject, QgsRasterLayer

# Check for sklearn availability
try:
    from sklearn.cluster import AgglomerativeClustering, DBSCAN, SpectralClustering
    sklearn_available = True
except ImportError:
    sklearn_available = False


class BandSelectionDialog(QDialog):
    """Dialog for selecting bands for a specific raster"""
    def __init__(self, raster_path, parent=None):
        super().__init__(parent)
        self.raster_path = raster_path
        self.setWindowTitle(f"Select Bands - {os.path.basename(raster_path)}")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        
        # Label
        label = QLabel(f"Select bands for: {os.path.basename(raster_path)}", self)
        layout.addWidget(label)
        
        # List widget for bands
        self.bandListWidget = QListWidget(self)
        self.bandListWidget.itemClicked.connect(self.toggle_item)
        layout.addWidget(self.bandListWidget)
        
        # Select/Unselect All buttons
        buttonLayout = QHBoxLayout()
        self.selectAllBtn = QPushButton("Select All", self)
        self.selectAllBtn.clicked.connect(self.select_all)
        self.unselectAllBtn = QPushButton("Unselect All", self)
        self.unselectAllBtn.clicked.connect(self.unselect_all)
        buttonLayout.addWidget(self.selectAllBtn)
        buttonLayout.addWidget(self.unselectAllBtn)
        layout.addLayout(buttonLayout)
        
        # OK and Cancel buttons
        okCancelLayout = QHBoxLayout()
        okBtn = QPushButton("OK", self)
        okBtn.clicked.connect(self.accept)
        cancelBtn = QPushButton("Cancel", self)
        cancelBtn.clicked.connect(self.reject)
        okCancelLayout.addWidget(okBtn)
        okCancelLayout.addWidget(cancelBtn)
        layout.addLayout(okCancelLayout)
        
        # Load bands
        self.load_bands()
    
    def toggle_item(self, item):
        """Toggle checkbox when item is clicked"""
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)
    
    def load_bands(self):
        """Load bands from the raster file"""
        self.bandListWidget.clear()
        if os.path.exists(self.raster_path):
            try:
                dataset = gdal.Open(self.raster_path)
                if dataset:
                    num_bands = dataset.RasterCount
                    for i in range(1, num_bands + 1):
                        band = dataset.GetRasterBand(i)
                        description = band.GetDescription() or f"Band {i}"
                        item = QListWidgetItem(description)
                        item.setCheckState(Qt.Checked)
                        item.setData(Qt.UserRole, i)  # Store band number
                        self.bandListWidget.addItem(item)
                    dataset = None
            except Exception as e:
                print(f"Error loading bands: {e}")
    
    def select_all(self):
        """Select all bands"""
        for i in range(self.bandListWidget.count()):
            self.bandListWidget.item(i).setCheckState(Qt.Checked)
    
    def unselect_all(self):
        """Unselect all bands"""
        for i in range(self.bandListWidget.count()):
            self.bandListWidget.item(i).setCheckState(Qt.Unchecked)
    
    def get_selected_bands(self):
        """Get list of selected band numbers"""
        selected = []
        for i in range(self.bandListWidget.count()):
            item = self.bandListWidget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected


class UnsupervisedClassifierDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Unsupervised Classifier")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumWidth(900)
        self.setWindowFlags(Qt.Dialog)
        
        self.layout = QVBoxLayout(self)
        
        # Store band selections for each raster
        self.band_selections = {}
        
        # ===== RASTER LAYERS TABLE SECTION =====
        self.rasterTableLabel = QLabel("Raster Layers for Batch Processing:", self)
        self.layout.addWidget(self.rasterTableLabel)
        
        # Create table for raster layers - 4 columns
        self.rasterTable = QTableWidget(self)
        self.rasterTable.setColumnCount(4)
        self.rasterTable.setHorizontalHeaderLabels(["Select", "Raster Name", "Output File Name", "Selected Bands"])
        self.rasterTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.rasterTable.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.rasterTable.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.rasterTable.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.rasterTable.setMinimumHeight(150)
        self.rasterTable.setRowCount(0)
        self.rasterTable.cellClicked.connect(self.table_cell_clicked)
        self.layout.addWidget(self.rasterTable)
        
        # Auto-populate from loaded layers
        self.populate_table_from_loaded_layers()
        
        # Table control buttons
        tableButtonLayout = QHBoxLayout()
        self.selectAllButton = QPushButton("Select All", self)
        self.selectAllButton.clicked.connect(self.toggle_select_all)
        self.selectAllButton.setMaximumWidth(150)
        
        self.removeButton = QPushButton("Remove from List", self)
        self.removeButton.clicked.connect(self.remove_selected_rows)
        self.removeButton.setMaximumWidth(150)
        
        self.selectBandsButton = QPushButton("Select Bands", self)
        self.selectBandsButton.clicked.connect(self.select_bands_for_selected)
        self.selectBandsButton.setMaximumWidth(150)
        
        tableButtonLayout.addWidget(self.selectAllButton)
        tableButtonLayout.addWidget(self.removeButton)
        tableButtonLayout.addWidget(self.selectBandsButton)
        tableButtonLayout.addStretch()
        self.layout.addLayout(tableButtonLayout)
        
        # Input selection (for adding multiple rasters from file)
        self.inputFileLabel = QLabel("Add Input Raster(s) from File:", self)
        self.layout.addWidget(self.inputFileLabel)
        
        self.inputFileLineEdit = QLineEdit(self)
        self.inputFileLineEdit.setReadOnly(True)
        self.inputFileButton = QPushButton("Browse...", self)
        self.inputFileButton.setMaximumWidth(100)
        self.inputFileButton.clicked.connect(self.select_input_files)
        
        self.inputFileLayout = QHBoxLayout()
        self.inputFileLayout.addWidget(self.inputFileLineEdit)
        self.inputFileLayout.addWidget(self.inputFileButton)
        self.layout.addLayout(self.inputFileLayout)
        
        # ===== OUTPUT FOLDER SECTION =====
        self.outputFolderLabel = QLabel("Output Folder:", self)
        self.layout.addWidget(self.outputFolderLabel)
        
        self.outputFolderLineEdit = QLineEdit(self)
        self.outputFolderButton = QPushButton("...", self)
        self.outputFolderButton.setMaximumWidth(50)
        self.outputFolderButton.clicked.connect(self.select_output_folder)
        
        self.outputFolderLayout = QHBoxLayout()
        self.outputFolderLayout.addWidget(self.outputFolderLineEdit)
        self.outputFolderLayout.addWidget(self.outputFolderButton)
        self.layout.addLayout(self.outputFolderLayout)
        
        # Checkbox for "Save output same as input"
        self.sameAsInputCheckBox = QCheckBox("Save output same as input folder?", self)
        self.sameAsInputCheckBox.stateChanged.connect(self.toggle_output_folder)
        self.layout.addWidget(self.sameAsInputCheckBox)
        
        # Algorithm selection
        self.algorithmLabel = QLabel("Select Clustering Method:", self)
        self.layout.addWidget(self.algorithmLabel)
        self.algorithmComboBox = QComboBox(self)
        self.algorithmComboBox.addItem("Kmeans (Best Method)")
        self.algorithmComboBox.addItem("ISODATA (Time Taking)")
        
        if sklearn_available:
            self.algorithmComboBox.addItem("Agglomerative Clustering")
            self.algorithmComboBox.addItem("DBSCAN")
            self.algorithmComboBox.addItem("Spectral Clustering")
        
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
        
        # Open output in QGIS
        self.openInQgisCheckBox = QCheckBox("Open the output in QGIS", self)
        self.layout.addWidget(self.openInQgisCheckBox)
        
        # ===== PROGRESS BAR SECTION =====
        self.progressLabel = QLabel("", self)
        self.layout.addWidget(self.progressLabel)
        
        self.progressBar = QProgressBar(self)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(True)
        self.progressBar.setFormat("%p% - %v/%m files")
        self.progressBar.hide()
        self.layout.addWidget(self.progressBar)
        
        # Run button
        self.runButton = QPushButton("Run Classification", self)
        self.layout.addWidget(self.runButton)
        
        # Connect signals
        self.algorithmComboBox.currentIndexChanged.connect(self.toggle_options)
        
        # Initial setup
        self.toggle_options()
        self.isodataOptionsGroupBox.hide()
        
        self.all_selected = True
    
    def populate_table_from_loaded_layers(self):
        """Automatically populate table with all loaded raster layers"""
        layers = QgsProject.instance().mapLayers().values()
        raster_layers = [layer for layer in layers if isinstance(layer, QgsRasterLayer)]
        
        for layer in raster_layers:
            self.add_raster_to_table_internal(layer.source())
    
    def table_cell_clicked(self, row, column):
        """Handle cell clicks - toggle on Select/Raster Name, make editable on Output Name"""
        # Toggle selection only on columns 0 (Select) and 1 (Raster Name)
        if column in [0, 1]:
            checkbox_widget = self.rasterTable.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(not checkbox.isChecked())
        
        # Make Output File Name column editable when clicked
        elif column == 2:
            output_item = self.rasterTable.item(row, 2)
            if output_item:
                # Enable editing
                output_item.setFlags(output_item.flags() | Qt.ItemIsEditable)
                self.rasterTable.editItem(output_item)
    
    def remove_selected_rows(self):
        """Remove selected rows from the table"""
        rows_to_remove = []
        for row in range(self.rasterTable.rowCount()):
            checkbox_widget = self.rasterTable.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    rows_to_remove.append(row)
        
        # Remove from bottom to top to maintain indices
        for row in sorted(rows_to_remove, reverse=True):
            raster_item = self.rasterTable.item(row, 1)
            if raster_item:
                input_path = raster_item.data(Qt.UserRole)
                # Remove from band selections
                if input_path in self.band_selections:
                    del self.band_selections[input_path]
            self.rasterTable.removeRow(row)
    
    def select_bands_for_selected(self):
        """Open band selection dialog for the currently highlighted (selected) row"""
        # Get the currently selected row
        current_row = self.rasterTable.currentRow()
        
        if current_row < 0:
            # No row is highlighted/selected
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self, 
                "No Row Selected", 
                "Please click on any input row in the table to select it, then click 'Select Bands'."
            )
            return
        
        # Get the raster item from the selected row
        raster_item = self.rasterTable.item(current_row, 1)
        if raster_item:
            input_path = raster_item.data(Qt.UserRole)
            self.open_band_selection_dialog(current_row, input_path)

    # def select_bands_for_selected(self):
    #     """Open band selection dialog for selected rasters"""
    #     for row in range(self.rasterTable.rowCount()):
    #         checkbox_widget = self.rasterTable.cellWidget(row, 0)
    #         if checkbox_widget:
    #             checkbox = checkbox_widget.findChild(QCheckBox)
    #             if checkbox and checkbox.isChecked():
    #                 raster_item = self.rasterTable.item(row, 1)
    #                 if raster_item:
    #                     input_path = raster_item.data(Qt.UserRole)
    #                     self.open_band_selection_dialog(row, input_path)
    #                     break  # Open only for first selected
    
    def open_band_selection_dialog(self, row, raster_path):
        """Open band selection dialog for specific raster"""
        dialog = BandSelectionDialog(raster_path, self)
        
        # Pre-select bands if already selected
        if raster_path in self.band_selections:
            selected_bands = self.band_selections[raster_path]
            for i in range(dialog.bandListWidget.count()):
                item = dialog.bandListWidget.item(i)
                band_num = item.data(Qt.UserRole)
                if band_num in selected_bands:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
        
        if dialog.exec_() == QDialog.Accepted:
            selected_bands = dialog.get_selected_bands()
            self.band_selections[raster_path] = selected_bands
            
            # Update the "Selected Bands" column
            bands_button = self.rasterTable.cellWidget(row, 3)
            if bands_button:
                label = bands_button.findChild(QLabel)
                if label:
                    label.setText(f"{len(selected_bands)} bands")
    
    def create_bands_cell_widget(self, row, raster_path):
        """Create cell widget with band count and ... button"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # Get band count
        try:
            dataset = gdal.Open(raster_path)
            num_bands = dataset.RasterCount if dataset else 0
            dataset = None
        except:
            num_bands = 0
        
        # Default: all bands selected
        if raster_path not in self.band_selections:
            self.band_selections[raster_path] = list(range(1, num_bands + 1))
        
        label = QLabel(f"{len(self.band_selections[raster_path])} bands")
        button = QPushButton("...")
        button.setMaximumWidth(30)
        button.clicked.connect(lambda: self.open_band_selection_dialog(row, raster_path))
        
        layout.addWidget(label)
        layout.addWidget(button)
        layout.addStretch()
        
        return widget
    
    def update_progress(self, current, total, message=""):
        """Update the progress bar and label"""
        self.progressBar.setMaximum(total)
        self.progressBar.setValue(current)
        self.progressLabel.setText(message)
        self.progressBar.show()
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
    
    def hide_progress(self):
        """Hide the progress bar and label"""
        self.progressBar.hide()
        self.progressLabel.setText("")
    
    def toggle_select_all(self):
        row_count = self.rasterTable.rowCount()
        if row_count == 0:
            return
        
        if self.all_selected:
            for row in range(row_count):
                checkbox_widget = self.rasterTable.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(False)
            self.selectAllButton.setText("Select All")
            self.all_selected = False
        else:
            for row in range(row_count):
                checkbox_widget = self.rasterTable.cellWidget(row, 0)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(True)
            self.selectAllButton.setText("Unselect All")
            self.all_selected = True
    
    def toggle_output_folder(self):
        if self.sameAsInputCheckBox.isChecked():
            self.outputFolderLineEdit.setEnabled(False)
            self.outputFolderButton.setEnabled(False)
            self.outputFolderLineEdit.clear()
        else:
            self.outputFolderLineEdit.setEnabled(True)
            self.outputFolderButton.setEnabled(True)
    
    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", "")
        if folder:
            self.outputFolderLineEdit.setText(folder)
    
    def select_input_files(self):
        """Select multiple input files"""
        filenames, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Input File(s)", 
            "", 
            "GeoTIFF Files (*.tif *.tiff);;All Files (*.*)"
        )
        
        if filenames:
            for filename in filenames:
                self.add_raster_to_table_internal(filename)
            
            # Update the line edit to show count
            self.inputFileLineEdit.setText(f"{len(filenames)} file(s) added")
    
    def add_raster_to_table_internal(self, input_file):
        """Internal method to add raster to table"""
        if not input_file or not os.path.exists(input_file):
            return
        
        # Check if already in table
        for row in range(self.rasterTable.rowCount()):
            raster_item = self.rasterTable.item(row, 1)
            if raster_item and raster_item.data(Qt.UserRole) == input_file:
                return
        
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        default_output_name = f"{base_name}_classified.tif"
        
        row_position = self.rasterTable.rowCount()
        self.rasterTable.insertRow(row_position)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.addWidget(checkbox)
        checkbox_layout.setAlignment(Qt.AlignCenter)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        self.rasterTable.setCellWidget(row_position, 0, checkbox_widget)
        
        # Raster name
        raster_item = QTableWidgetItem(base_name)
        raster_item.setFlags(raster_item.flags() & ~Qt.ItemIsEditable)
        raster_item.setData(Qt.UserRole, input_file)
        self.rasterTable.setItem(row_position, 1, raster_item)
        
        # Output name (initially not editable, becomes editable on click)
        output_item = QTableWidgetItem(default_output_name)
        output_item.setFlags(output_item.flags() & ~Qt.ItemIsEditable)  # Initially not editable
        self.rasterTable.setItem(row_position, 2, output_item)
        
        # Bands selection
        bands_widget = self.create_bands_cell_widget(row_position, input_file)
        self.rasterTable.setCellWidget(row_position, 3, bands_widget)
        
        self.rasterTable.setRowHeight(row_position, 35)
    
    def get_selected_rasters(self):
        """Get list of selected rasters with their output names, paths, and bands"""
        selected = []
        for row in range(self.rasterTable.rowCount()):
            checkbox_widget = self.rasterTable.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                
                if checkbox and checkbox.isChecked():
                    raster_item = self.rasterTable.item(row, 1)
                    output_item = self.rasterTable.item(row, 2)
                    
                    if raster_item and output_item:
                        input_path = raster_item.data(Qt.UserRole)
                        output_name = output_item.text()
                        
                        # Get selected bands
                        selected_bands = self.band_selections.get(input_path, [])
                        
                        if self.sameAsInputCheckBox.isChecked():
                            input_dir = os.path.dirname(input_path)
                            output_path = os.path.join(input_dir, output_name)
                        else:
                            output_folder = self.outputFolderLineEdit.text()
                            if output_folder:
                                output_path = os.path.join(output_folder, output_name)
                            else:
                                input_dir = os.path.dirname(input_path)
                                output_path = os.path.join(input_dir, output_name)
                        
                        selected.append({
                            'input': input_path,
                            'output': output_path,
                            'bands': selected_bands
                        })
        return selected
    
    def toggle_options(self):
        if self.algorithmComboBox.currentText() == "ISODATA (Time Taking)":
            self.isodataOptionsGroupBox.show()
        else:
            self.isodataOptionsGroupBox.hide()
        self.adjustSize()
