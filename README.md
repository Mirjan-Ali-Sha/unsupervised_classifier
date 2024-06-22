# Unsupervised Classifier:
The Unsupervised Classification Plugin for QGIS is a powerful tool designed to facilitate the classification of satellite images using unsupervised learning algorithms. 
This plugin provides an easy-to-use interface for loading satellite images and selecting from a variety of unsupervised classification methods, including K-means and ISODATA. 
## Key Features: 
1. __User-Friendly Interface:__ Intuitive dialog for selecting classification parameters. 
2. __Multiple Algorithms:__ Support for K-means and ISODATA algorithms. 
3. __Seamless Integration:__ Directly integrates with QGIS, allowing for easy access and visualization of classification results. 
4. __Flexible:__ Handles different types of satellite images and provides robust classification results. 
This plugin is ideal for remote sensing professionals, GIS analysts, and researchers looking to perform efficient and accurate unsupervised classification of satellite imagery within the QGIS environment. 
### To use this Tool follow the below steps: 
1. Click on the tool or chose __"Raster"__ menu --> __"MAS Raster Processing"__ menu item --> __"Unsupervised Classifier"__ option. 
2. Select 'Stack Image' or Image as Input and select output file name. 
3. Select clustering method. 
4. Adjust all parameters according to your needs. 
_'Number of Bands:'_ give you total number of bands, If you decrease it then it will remove that no of bands from process the clustering. 
or you can directly select those bands by check mark on _'Do you want to select available bands?'_ 
5. Decide do you wants to open the output or not (By marking on _"Do you want to open output in QGIS Interface?"_). 
6. Click on __"Run Clustering"__ button. 
### 
** **Note:** After installation make sure the following points; 
1. Check Mark the Installed plugins (under 'Manage and Install Plugins...' menu) 
2. Check Mark 'MAS Raster Processing' toolbar (by right click on toolbar).
