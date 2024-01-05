# docker build -t jrce1/lisflood .
# docker push jrce1/lisflood

FROM continuumio/miniconda3
LABEL maintainer="Stefania Grimaldi, Cinzia Mazzetti, Carlo Russo, Valerio Lorini, Ad de Roo"

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
COPY src/lisfloodSettings_reference.xml /
COPY LICENSE /
COPY VERSION /

# RUN Tests
COPY tests/. /tests/
COPY pytest.ini /tests
RUN conda run -n lisflood python -m pytest /tests -x -l -ra

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
