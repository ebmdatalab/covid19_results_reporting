# DIssemination of REgistered COVID-19 Clinical Trials (DIRECCT)

This repo contains Python code for data collection, cleaning, and analysis for Phase 1 of the DIRECCT project along with intermediary datasets.

For additional project code in R see: https://github.com/maia-sh/direcct

## Docker Details

This repo includes a Docker container with the environment necessary to run all included code.

Details on installing Docker, please see the [`INSTALLATION_GUIDE.md`](INSTALLATION_GUIDE.md)

## Project Code

The project code lives in six notebooks in the `Notebooks` folder.

1. Data Cleaning - This notebook takes the ICTRP collection of COVID-19 registered trials and cleans it, accounts for known cross-registrations, and adds some additional data manually extracted from free-text fields. Also produces a preliminarily filtered version of the dataset to be used for scraping in Notebook 3
2. PubMed and Cord-19 Searches - This notebook conducts a pubmed search and then searches the results and the [CORD-19](https://www.semanticscholar.org/cord19/download) database for references to trial ids or registries. Note, the CORD-19 dataset is too big to fit in the repo but historic archives of the dataset are maintained at https://ai2-semanticscholar-cord-19.s3-us-west-2.amazonaws.com/historical_releases.html
3. Registry Scraping - Includes the code necessary to scrape various registries for key information not provided in the ICTRP.
4. Registry Data Hanlding - Gets the data from the registry scrapes into a usable format.
5. Final Data Combining - Bringing all the datasets together into a single dataset. This Notebook has largely been replaced with equivalent R code in our other [project repo](https://github.com/maia-sh/direcct) but we maintain an archive here.
6. Analyses and Figures - Survival analysis and some figure creation is implement in this Notebook. Additional analysis done in our [R repo](https://github.com/maia-sh/direcct). 

## How to cite

Please cite our paper when available. Our dataset can also be cited, available [here](https://www.doi.org/10.5281/zenodo.4669937).
