<h1 align="center"> EMIT Applications Support for Acid Mine Drainage Assessment </h2>

# Overview

Welcome to the repository for the EMIT Applications Support for Acid Mine Drainage Assessment. In this repository, we are investigating the application of data from the Earth Surface Mineral Dust Source Investigation (EMIT) to assessing mined lands for the presence or future risk of acid mine drainage (AMD). Leveraging EMIT's surface mineralogy identifications, we are developing methods of using remotely sensed mineral assemblages to characterize AMD risk on mined lands. The goal is to formulate a data product that can be utilized by stakeholders in assessing managed lands for AMD, and to aid in decisions on where to allocate remediation resources. 

# Introduction
Acid mine drainage is widely recognized as one of the mining industry’s largest environmental problems. When iron sulfide minerals are exposed to air and water by mining activities, they react to form sulfuric acid and often release toxic metals. The acidity and toxic metal release is a significant environmental hazard, destroying stream habitats and contaminating water supplies. The problem is pervasive in the western United States. The BLM & USFS records indicate there are over 100,000 abandoned mine sites in this region, and estimates indicate that over 80% of them require evaluation and/or remediation for AMD. The USFS estimates that drainage from abandoned mines is impacting 8,000 to 16,000 km of streams are impacted. This issue is not restricted to the southwest US as one estimates suggests that globally between 17 and 27 billion gallons of water per year are polluted by these reactions.

As these numbers suggest, the scale of this issue is vast as these abandoned mines are significant in number, are often in hard-to-reach locations, and frequently land managers and stakeholders often have limited remediation resources. With these limited resources, land managers and stakeholders often need to down-select candidate remediation sites which can prove tricky if they are in remote locations or great in number. As EMIT is collecting relevant mineralogical data across the conterminous United States, the possibility exists that applying these data to this problem may assist these stakeholders in the assessment of AMD on managed lands and the direction of remediation resources.

# Background and Mineralogy
The Earth surface Mineral dust source InvesTigation (EMIT) mission was installed on the International Space Station in 2022 and has been collecting visible to shortwave infrared spectra of Earth’s surface ever since (Green et al., 2020). The primary goal for these imaging spectroscopy data was to identify the abundance of surface minerals in arid dust-producing regions and then assess the radiative forcing effect of these aerosols in Earth’s atmosphere. These mineralogy detections provide information for other applications, especially ones that can leave mineralogical signals on the surface.

EMIT is a Visible to Short Wavelength Infrared (VSWIR, 380-2500 nm) imaging spectrometer. It collects a two-dimensional picture of the surface and for each pixel of the image a spectrum is collected covering this spectral range. The VSWIR spectrum is sampled at 7.4 nm. The measured radiance of the surface is converted to a reflectance spectrum using the workflows developed in the [EMIT Core Science Data System (SDS)](https://github.com/emit-sds). The EMIT data and more information on the individual EMIT products can be found at the [LP DAAC]( https://lpdaac.usgs.gov/products/emitl2bminv001). These reflectance spectra are then processed through the Tetracorder algorithm (Clark et al., 2024) into the [Level 2B mineralogy product](https://github.com/emit-sds/emit-sds-l2b). These L2B mineralogy data are what we primarily explore in this product, however, for the EMIT aerosol radiative forcing investigation the data the data continue down a processing pipeline into Earth system models.

The mechanisms leading to acid mine drainage leaves a trace of characteristic minerals on the surface, and therefore mineralogy is an important indicator of the occurrence of these reactions. Sulfides such as pyrite are the primary mineralogy of AND are a good indicator for AMD potential when they are observed. However, pyrite is notoriously difficult to identify in remotely sense spectral data. Its VSWIR spectrum is dominated by very broad and strongly absorbing iron charge transfer features that result in the mineral having very low reflectance at these wavelengths and not much spectral definition. Therefore, we turn to the secondary minerals of AMD for this investigation.

Secondary minerals formed and precipitated from the generated acidic fluids such as sulfates (jarosite, schwertmannite, copiapite, etc.) can indicate AMD has occurred or is occurring. These sulfate minerals form in relatively specific pH conditions, and, as such, can be used as an indicator for the acidity of their formation environment. For example, jarosite, schwertmannite, and then copiapite form from fluids of increasing pH and if such a progression was observed it could suggest a path leading towards an acidic source. Similarly, these minerals have variable surface residency times and factors such as their stability in the surface environment or their susceptibility to weathering alter how long they can be observed. The surface residency time somewhat follows the formation acidity as schwertmannite is metastable at the surface and can convert to goethite over a handful of years and copiapite is highly soluble and its observation suggests it was formed relatively recently. These key AMD minerals have diagnostic absorption features in the VSWIR spectral range and thankfully were included in the [suite of endmembers]( https://github.com/emit-sds/emit-sds-l2b/blob/develop/data/mineral_grouping_matrix_20230503.csv) used in the production of the EMIT L2B mineralogy product.

# Motivation
A primarily motivation for exploring this application of EMIT data draws from an USGS & EPA study of the California Gulch Superfund Site near Leadville, CO using the Airborne Visible Infrared Imaging Spectrometer (AVIRIS, Swayze et al., 2000). AVIRIS is an imaging spectrometer system collecting similar data as EMIT except from an airborne platform as opposed to observing from orbit on the International Space Station. In the late-90s, AVIRIS overflew the California Gulch Superfund Site and collected VSWIR data in situ across a traverse with a handheld spectrometer for ground truth. This investigation assisted the EPA in deciding where to direct remediation resources highlighting the potential of these data for this application. In the end, the airborne spectroscopy investigation was stated by the EPA to have shortened the remediation efforts by 2.5 years and saved the project two million dollars. This Leadville investigation is not the only application of imaging spectroscopy to investigating locations with AMD, and several studies to date have investigated this topic (e.g., Zabcic et al., 2014; Farrand & Bhattacharya, 2021; Flores et al., 2021). This led us to ask whether we can build upon this successful application at Leadville and, using EMIT’s greater coverage from orbit, aid in identifying acid mine drainage on abandoned mined lands in the western US?

# EMIT Applications Support for Acid Mine Drainage Assessment
The AMD product of this investigation utilizes the [EMITL2BMIN](https://lpdaac.usgs.gov/products/emitl2bminv001/) data product and the minerals identified therein to screen active and abandoned mined lands for AMD. This product is described as containing the “mineralogy derived from fitting reflectance spectra, screening for non-mineralogical components” (Brodrick et al., 2023). The key outputs of the data processing are two “groups” of mineral endmembers derived from the Tetracorder algorithm. These include Group 1 which derives mineral identifications from electronic absorptions in the visible and 1-micron regions and Group 2 which derives mineral identifications from narrow absorptions in the 2 to 2.5-micron region (e.g., clays, carbonates, sulfates). The AMD-relevant mineral endmembers have diagnostic absorption features in both wavelength ranges. The EMITL2BMIN data consists of two delivered products. First, the “EMIT L2B Estimated Mineral Identification and Band Depth 60 m”, which consist of data cubes where “the first band contains the Group 1 band depth, the second band contains the Group 1 mineral identification, the third band contains the Group 2 band depth, and the fourth band contains the Group 2 mineral identification” (Brodrick et al., 2023). Second, the “EMIT L2B Estimated Mineral Identification and Band Depth Uncertainty 60 m”, which consists of data cubes where “the first band contains the Group 1 band depth uncertainty, the second band contains the fit score (R<sup>2</sup>) of the mineral match, the third band contains the Group 2 band depth uncertainty, and the fourth band contains the Group 2 fit score (R<sup>2</sup>)” (Brodrick et al., 2023). Additionally, our processing pipeline includes the EMIT cloud mask that is currently a component of the [L2A Estimated Surface Reflectance]( https://www.earthdata.nasa.gov/data/catalog/lpcloud-emitl2arfl-001).

Our algorithm reclassifies the inputted EMIT EMITL2BMIN data into an aggregated product with mineral groups chosen to help assess AMD risk. It also incorporates EMIT quality controls (cloud masking, spectral fit values, uncertainty, etc.). Based on experimental studies and field investigations in the literature as well as past AVIRIS studies, we developed a mineralogical classification scale that maps out indicator minerals of acidity and related toxic metal leachability. The AMD mineral groups consist of (1) primary mineralogy that can lead to AMD (such as primary sulfides like pyrite), (2) secondary mineralogy resulting from AMD (e.g., acidic sulfates formed from acidic environments), and (3) buffering mineralogy to AMD reactions (such as carbonates).

# Input/Output
## Data inputs 
This repository is designed to ingest EMITL2BMIN granules and derivative products containing the same type of mineral identification and mineral band depth raster data bands. The setup of configuration parameters for image processing is managed by the [mlky](https://github.com/jammont/mlky) package and the details are contained in the `config.yml` file. The `config.yml` must be edited to point to the data directory with the file(s) to be processed and output directory as well as a flag denoting whether the data are included in subdirectories or not (see Downloader). Also found in this config file are several versions of the remapping algorithm grouped by their mineralogy in the comments. Various versions have been developed and investigated and have variations in the parameters for the endmembers called for classification, the filtering of mineral identifications by fit and/or band depth, the application of the cloud mask bands, and the colorization of the output. We have explored several variations of these parameters (as can be seen in the preserved versions seen in the config file) and the current iteration has settled on version 5 (v5). See the comments in the configuration file for a description of the different versions and components. 
Using the command:``` amd config generate``` will create a blank version of the configuration with all the available options listed and briefly described.

## Example Execution Command

The processing of EMIT images is executed using the `amd` command:

```
amd --help
```

The `run` command performs the image processing and parameters from the configuration file are patched in. Below is an example call to generate EMIT acid mine drainage product:

```
amd run -c config.yml -p "default<-local<-v1"
```

Patching (with -p) of multiple options or different variations from the configuration file are possible:

```
amd run -c ./configs/config.yml -p "default<-local<-v1<-v3<-loc1<-quiet"
```


## Data outputs
The outputs of the processing routines are controlled within the `config.yml` file. The processing steps can output three main data products with four sub-products each. An AMD-classified image can be outputted for the `group_1` minerals, the `group_2` minerals, as well as a `merged` product of the two groups. Four sub-products are possible with each data product: A numerical data version (`mineral_id`) of the product where each pixel contains the identification number for the AMD-relevant mineralogy in (1) a NetCDF (`.nc`) and/or (2) geoTIFF (`.tiff`) format. An RGBA colorized version (`-color`) of the product available in (3) NetCDF and (4) geoTIFF formats. From the command line, specific mineral groups or desired output products can be called, and the outputs of specific formats can be turned on/off in the `config.yml` file.

An example of all four images generated for both group_1 and group_2 minerals as well as the merged images are as follows for image EMIT_L2B_MIN_001_20220819T201130_2223113_016:

```
EMIT_L2B_MIN_001_20220819T201130_2223113_016_group_1_mineral_id-color.nc
EMIT_L2B_MIN_001_20220819T201130_2223113_016_group_1_mineral_id-color.tiff
EMIT_L2B_MIN_001_20220819T201130_2223113_016_group_1_mineral_id.nc
EMIT_L2B_MIN_001_20220819T201130_2223113_016_group_1_mineral_id.tiff
EMIT_L2B_MIN_001_20220819T201130_2223113_016_group_2_mineral_id-color.nc
EMIT_L2B_MIN_001_20220819T201130_2223113_016_group_2_mineral_id-color.tiff
EMIT_L2B_MIN_001_20220819T201130_2223113_016_group_2_mineral_id.nc
EMIT_L2B_MIN_001_20220819T201130_2223113_016_group_2_mineral_id.tiff
EMIT_L2B_MIN_001_20220819T201130_2223113_016_merged-color.nc
EMIT_L2B_MIN_001_20220819T201130_2223113_016_merged-color.tiff
EMIT_L2B_MIN_001_20220819T201130_2223113_016_merged.nc
EMIT_L2B_MIN_001_20220819T201130_2223113_016_merged.tiff
```
# Tutorial Jupyter Notebook
We have developed a Jupyter Notebook that steps through hand describes several of the commands and approaches utilized in our product. This can be found in the “notebooks” folder of the repository.
# Comparison with other databases
When mineral assemblages of concern are compared with mine data bases such as the [USMIN](https://www.usgs.gov/centers/gggsc/science/usmin-mineral-deposit-database) data base, locations that may warrant more detailed investigation can be identified. Similarly, cross comparing the AMD mineral assemblages with hydrographical data such as the [National Hydrography Dataset](https://www.usgs.gov/national-hydrography/national-hydrography-dataset) can be a powerful approach as relating the AMD mineralogy to hydrological gradients or watersheds will help inform the end user on possible acidification of local surface waters and the path of this acidity.

# References
<ul>
<li>Brodrick, P. G., Clark, R. N., Swayze, G. A., Kokaly, R., Meyer, J., Ehlmann, B., Keebler, A., Thompson, D. R., & Green, R. O. (2023). EMIT L2b Algorithm: Mineral Detection and Related Products at the Pixel Scale---Theoretical Basis (EMITL2B_ATBD_v1) [Technical report]. NASA Jet Propulsion Laboratory.</li>
<li>Clark, R. N., Swayze, G. A., Livo, K. E., Brodrick, P. G., Dobrea, E. N., Vijayarangan, S., ... & Querol, X. (2024). Imaging Spectroscopy: Earth and Planetary Remote Sensing with the PSI Tetracorder and Expert Systems from Rovers to EMIT and Beyond. The Planetary Science Journal, 5(12), 276.</li>
<li>Farrand, W. H., & Bhattacharya, S. (2021). Tracking acid generating minerals and trace metal spread from mines using hyperspectral data: case studies from Northwest India. International Journal of Remote Sensing, 42(8), 2920-2939.</li>
<li>Flores, H., Lorenz, S., Jackisch, R., Tusa, L., Contreras, I. C., Zimmermann, R., & Gloaguen, R. (2021). UAS-based hyperspectral environmental monitoring of acid mine drainage affected waters. Minerals, 11(2), 182.</li>
<li>Green, R. O., Mahowald, N., Ung, C., Thompson, D. R., Bator, L., Bennet, M., ... & Zan, J. (2020, March). The Earth surface mineral dust source investigation: An Earth science imaging spectroscopy mission. In 2020 IEEE aerospace conference (pp. 1-15). IEEE.</li>
<li>Swayze, G. A., Smith, K. S., Clark, R. N., Sutley, S. J., Pearson, R. M., Vance, J. S., ... & Roth, S. (2000). Using imaging spectroscopy to map acidic mine waste. Environmental Science & Technology, 34(1), 47-54.</li>
<li>Zabcic, N., Rivard, B., Ong, C., & Müller, A. (2014). Using airborne hyperspectral data to characterize the surface pH and mineralogy of pyrite mine tailings. International Journal of Applied Earth Observation and Geoinformation, 32, 152-162.</li>
</ul>

# Acknowledgements
This work has been supported by funding from the Earth System Science Pathfinder Program Office (ESSP PO).
<img width="468" height="657" alt="image" src="https://github.com/user-attachments/assets/c28fc8d5-a857-4847-ab14-4f8d6f783f0e" />
