# Source utilities

This portfolio V1 keeps the full research sequence in inspectable notebooks and
uses two small command-line utilities:

- `download_puffer_sample.py`: safely downloads and extracts Puffer's official fake
  sample for schema exploration;
- `make_readme_figures.py`: regenerates the two aggregate figures embedded in the
  project README.

The multi-gigabyte real-data transformation is documented in
`notebooks/02_target_definition.ipynb`. A future productionization phase would move
that pipeline into tested modules; V1 does not pretend those modules already exist.

