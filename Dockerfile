# docker build -t efas/lisflood .
# docker push efas/lisflood

FROM continuumio/miniconda3
MAINTAINER Domenico Nappo <domenico.nappo@gmail.com>

ENV DEBIAN_FRONTEND=noninteractive

# Install requirements
RUN apt-get update && \
    apt-get -y install gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Create conda "lisflood" environment:
COPY environment.yml .
RUN conda update -n base -c defaults conda
RUN conda env create -n lisflood -f environment.yml
#RUN conda install -n lisflood -c conda-forge GDAL==`conda run -n lisflood gdal-config --version`

#COPY requirements.txt /
#RUN conda run -n lisflood pip install -r /requirements.txt --ignore-installed

# Copy source code
COPY src/lisflood/. /lisflood/
COPY src/lisf1.py /
COPY src/settings_tpl.xml /
COPY LICENSE /
COPY VERSION /

# Compile kwpt
RUN cd /lisflood/hydrological_modules && conda run -n lisflood python compile_kinematic_wave_parallel_tools.py build_ext --inplace

# RUN Tests
COPY tests/. /tests/
COPY pytest.ini /tests
RUN conda run -n lisflood python -m pytest /tests -x -l -ra

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
