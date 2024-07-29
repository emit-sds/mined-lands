<h1 align="center"> mined-lands </h1>

<h2 align="center"> EMIT Applications Support for Acid Mine Drainage Assessment </h2>

# Description

Welcome to the EMIT mined-lands repository. In this actively-developing repository, we are investigating the application of data from the Earth Surface Mineral Dust Source Investigation (EMIT) to assessing mined lands for the presence or future risk of acid mine drainage (AMD). Leveraging EMIT's surface mineralogy identifications, we are developing methods of using the specific remotely-sened mineral assemblages 
to characterize AMD risk on mined lands. The goal is to formulate a data product that can be utilized by stakeholders in assessing managed lands for AMD, and to aid in decisions on where to allocate remediation resources. When mineral assemblages of concern are compared with mine data bases such as the [USMIN](https://www.usgs.gov/centers/gggsc/science/usmin-mineral-deposit-database) data base, locations that may warrant more detailed investigation can be identified. This work builds on past airborne investigations of locations with AMD using high spectral resolution imaging spectroscopy (e.g., Swayze et al., 2000, Farrand & Bhattacharya, 2021).

The first iteration of this investigation utilizes the [EMITL2BMIN](https://lpdaac.usgs.gov/products/emitl2bminv001/) data products and the minerals identified therein to screen active and abandoned mined lands for AMD. The process reclassifies the inputted EMIT EMITL2BMIN data into an aggregated product with mineral groups chosen to help assess AMD risk. These groups consist of (1) primary mineralogy that can lead to AMD (such as primary sulfides like pyrite), (2) secondary mineralogy resulting from AMD (e.g., acidic sulfates formed from acidic environments), and (3) buffering mineralogy to AMD reactions (such as carbonates).

# Input/Output

## Data inputs 
The current version of the repository is designed to ingest EMITL2BMIN granules and derivative products containing the same type of mineral identification and mineral band depth raster data bands. The `config.yml` must be edited to point to the data directory and to the file to be processed.

## Data outputs
The outputs of the processing routines are controlled within the `config.yml` file. The processing steps can output three main data products with four sub-products each. An AMD-classified image can be outputted for the `group_1` minerals, the `group_2` minerals, as well as a `merged` product of the two groups. Four sub-products are possible with each data product: A numerical data version (`mineral_id`) of the product where 
each pixel contains the identification number for the AMD-relevant mineralogy in (1) a NetCDF (`.nc`) and/or (2) geoTIFF (`.tiff`) format. An RGBA colorized version (`-color`) of the product available in (3) NetCDF and (4) geoTIFF formats. From the command line, specific minearl groups or desired output products can be called, and the outputs of specific formats can be turned on/off in the `config.yml` file.

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

## Example Execution Command

The setup of configuration parameters for image processing is managed by the [mlky](https://github.com/jammont/mlky) package and the details are contained in the `config.yml` file.

The processing of EMIT images is executed using the `amd` command-line command:

```
amd --help
```

The `run` command performs the image processing and parameters from the configuration file are patched in. Below is an example call to generate EMIT acid mine draining product:

```
amd run -c config.yml -p "default<-local<-v1"
```

Patching of multiple options or different variations from the 
configuration file are possible:

```
amd run -c ./configs/config.yml -p "default<-local<-v1<-v3<-loc1<-quiet"
```

# References

Farrand, W. H., & Bhattacharya, S. (2021). Tracking acid generating minerals and trace metal spread from mines using hyperspectral data: case studies from Northwest India. International Journal of Remote Sensing, 42(8), 2920-2939.

Swayze, G. A., Smith, K. S., Clark, R. N., Sutley, S. J., Pearson, R. M., Vance, J. S., ... & Roth, S. (2000). Using imaging spectroscopy to map acidic mine waste. Environmental Science & Technology, 34(1), 47-54.

# Acknowledgements
This work has been supported by funding from the Earth System Science Pathfinder Program Office (ESSP PO). 
