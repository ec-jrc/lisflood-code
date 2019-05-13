FROM python:2.7.16-stretch
MAINTAINER Domenico Nappo <domenico.nappo@gmail.com>

ENV no_proxy=jrc.it,localhost,ies.jrc.it,127.0.0.1,jrc.ec.europa.eu
ENV ftp_proxy=http://10.168.209.72:8012
ENV https_proxy=http://10.168.209.72:8012
ENV http_proxy=http://10.168.209.72:8012
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=/opt/cmake-3.14.1-Linux-x86_64/bin:/opt/pcraster/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH}
ENV PYTHONPATH=/opt/pcraster/python:${PYTHONPATH}
ENV TZ=Europe/RomeB

RUN echo 'Acquire::https::Proxy "http://10.168.209.72:8012";' >> /etc/apt/apt.conf.d/30proxy \
    && echo 'Acquire::http::Proxy "http://10.168.209.72:8012";' >> /etc/apt/apt.conf.d/30proxy
RUN apt-get update && apt-get install -y --no-install-recommends software-properties-common apt-file apt-utils
RUN apt-file update

RUN apt install -y --no-install-recommends gcc g++ git libboost-all-dev libpython-dev libxerces-c-dev libxml2 libxml2-utils libxslt1-dev qtbase5-dev \
    libqwt-dev gfortran gdal-bin libgdal-dev python-gdal libqt5opengl5 libqt5opengl5-dev qtbase5-dev \
    && pip install docopt numpy==1.15 pytest pandas

WORKDIR /opt
RUN wget https://cmake.org/files/LatestRelease/cmake-3.14.1-Linux-x86_64.tar.gz && tar -xzvf cmake-3.14.1-Linux-x86_64.tar.gz \
    && wget http://pcraster.geo.uu.nl/pcraster/4.2.1/pcraster-4.2.1.tar.bz2 && tar xf pcraster-4.2.1.tar.bz2 \
    && mkdir /lisflood && mkdir /input && mkdir /output \
    && mkdir /tests && mkdir /usecases \
    && cd pcraster-4.2.1 && mkdir build && cd build \
    && cmake -DFERN_BUILD_ALGORITHM:BOOL=TRUE -DCMAKE_INSTALL_PREFIX:PATH=/opt/pcraster /opt/pcraster-4.2.1/ && cmake --build ./ && make install

COPY requirements.txt /
RUN pip install -r /requirements.txt
COPY LICENSE /
COPY docker-entrypoint.sh /
COPY src/lisflood/. /lisflood/
COPY src/settingsEUMerged.xml /lisflood/
WORKDIR /lisflood/hydrological_modules
RUN python compile_kinematic_wave_parallel_tools.py build_ext --inplace
WORKDIR /

ENTRYPOINT ["/docker-entrypoint.sh"]
