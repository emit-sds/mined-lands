<h1 align="center"> mined-lands </h1>

EMIT Applications Support for Acid Mine Drainage Assessment

# Description

Welcome to th EMIT mined-lands repository. In this actively-developing repository, we are investigating the application of data from the Earth Surface Mineral Dust Source Investigation (EMIT) to assessing mined lands for the presence or future risk of acid mine drainage (AMD). Leveraging EMIT's surface mineralogy identifications, we are developing methods of using the specific remotely-sened mineral assemblages 
to characterize AMD risk on mined lands. The goal is to formulate a data product that can be utilized by stakeholders in assessing managed lands for AMD, and to aid in decisions on where to allocate remediation resources. When these mineral assemblages of AMD concern are compared with mine data bases such as the [USMIN](https://www.usgs.gov/centers/gggsc/science/usmin-mineral-deposit-database) data base, the likelihood of a location requiring possible more detailed investigation can be quantified. This work builds on past airborne investigations of locations with AMD using high spectral resolution imaging spectroscopy (e.g., Swayze et al., 2000, Farrand & Bhattacharya, 2021).

The first iteration of this investigation utilizes the  [EMITL2BMIN](https://lpdaac.usgs.gov/products/emitl2bminv001/) data products and the minerals identified therein to screen active and abandoned mined lands for AMD. The process reclassifies the inputted EMIT EMITL2BMIN data into a new product with new mineral groups chosen to help assess AMD risk. These groups consist of (1) primary mineralogy that can lead to AMD (such as primary sulfides like pyrite), (2) secondary mineralogy resulting from AMD (e.g., acidic sulfates formed from acidic environments), and (3) buffering mineralogy to AMD reactions (such as carbonates).

# Input/Output

## Data inputs 
The current version of the repository is designed to ingest EMITL2BMIN granules and derivative products containing the same type of mineral identification and mineral band depth raster data bands. The config.yml must be edited to point to the data directory and to the file to be processed.

## Data outputs
The processing steps will output three main data products with four sub-products each.
An AMD-classified image with be outputted for the group_1 minerals, the group_1 minerals, as well as a merged product of the two groups. Four sub-products are included with each data product: (1) a NetCDF and (2) geoTIFF version of the product, as well as RGBA colorized versions of the AMD product also in (3) NetCDF and (4) geoTIFF formats. From the command line, specific minearl groups or desired output products can be called.

## Example Execution Command

Example call to generate EMIT acid mine draining product:

```
python minerals.py -c configs/config.yml -p "default<-local<-full"
```

# References

Farrand, W. H., & Bhattacharya, S. (2021). Tracking acid generating minerals and trace metal spread from mines using hyperspectral data: case studies from Northwest India. International Journal of Remote Sensing, 42(8), 2920-2939.

Swayze, G. A., Smith, K. S., Clark, R. N., Sutley, S. J., Pearson, R. M., Vance, J. S., ... & Roth, S. (2000). Using imaging spectroscopy to map acidic mine waste. Environmental Science & Technology, 34(1), 47-54.