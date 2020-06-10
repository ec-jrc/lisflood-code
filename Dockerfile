# docker build -t efas/lisflood .
# docker push efas/lisflood

FROM continuumio/miniconda3
MAINTAINER Domenico Nappo <domenico.nappo@gmail.com>

ENV DEBIAN_FRONTEND=noninteractive

# Create conda "lisflood" environment:
COPY environment.yml .
RUN conda env create -f environment.yml
RUN conda install -n lisflood -c conda-forge GDAL==`conda run -n lisflood gdal-config --version`

# Install requirements
COPY requirements.txt /
RUN conda run -n lisflood pip install -r /requirements.txt

# Copy source code
WORKDIR /
COPY src/lisflood/. /lisflood/
COPY src/lisf1.py /
COPY src/settings_tpl.xml /
COPY LICENSE /

# Compile kwpt
WORKDIR /lisflood/hydrological_modules
RUN conda run -n lisflood python compile_kinematic_wave_parallel_tools.py build_ext --inplace

# RUN Tests
WORKDIR /
COPY tests/. /tests/
COPY pytest.ini /tests
RUN conda run -n lisflood python -m pytest /tests -x -l -ra

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
