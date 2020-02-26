FROM python:3.6-buster
MAINTAINER Domenico Nappo <domenico.nappo@gmail.com>

ENV no_proxy=jrc.it,localhost,ies.jrc.it,127.0.0.1,jrc.ec.europa.eu
ENV ftp_proxy=http://10.168.209.72:8012
ENV https_proxy=http://10.168.209.72:8012
ENV http_proxy=http://10.168.209.72:8012
ENV DEBIAN_FRONTEND=noninteractive
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV PATH=/opt/pcraster36/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH}
ENV PYTHONPATH=/opt/pcraster36/python:${PYTHONPATH}
ENV TZ=Europe/RomeB

RUN echo 'Acquire::https::Proxy "http://10.168.209.72:8012";' >> /etc/apt/apt.conf.d/30proxy \
 && echo 'Acquire::http::Proxy "http://10.168.209.72:8012";' >> /etc/apt/apt.conf.d/30proxy

RUN apt-get update && apt-get install -y --no-install-recommends software-properties-common apt-file apt-utils
RUN apt-file update
RUN apt-get install -y --no-install-recommends gcc g++ git cmake python3.6 python3-pip bzip2 python3-dev mlocate \
                    qtbase5-dev libncurses5-dev libqwt-qt5-dev libqt5opengl5-dev libqt5opengl5 python3-setuptools \
                    build-essential libxerces-c-dev libboost-all-dev gdal-bin libgdal-dev wget \
  && apt-get clean && apt-get autoremove && updatedb

RUN python3.6 -m pip install --upgrade pip && python3.6 -m pip install numpy==1.17.2 GDAL==`gdal-config --version` \
    docopt==0.6.2 nine

WORKDIR /opt
RUN wget -q http://pcraster.geo.uu.nl/pcraster/4.2.1/pcraster-4.2.1.tar.bz2 && \
    tar xf pcraster-4.2.1.tar.bz2 && rm pcraster-4.2.1.tar.bz2 && mkdir /opt/pcraster-4.2.1/build && \
    mkdir -p /lisflood && mkdir -p /input && mkdir -p /output && mkdir -p /tests && mkdir -p /usecases && mkdir -p /data

WORKDIR /opt/pcraster-4.2.1/build
RUN strip --remove-section=.note.ABI-tag /usr/lib/x86_64-linux-gnu/libQt5Core.so.5
RUN cmake -DFERN_BUILD_ALGORITHM:BOOL=TRUE -DCMAKE_INSTALL_PREFIX:PATH=/opt/pcraster36 -DPYTHON_EXECUTABLE:FILEPATH=`which python3.6` ../ \
 && cmake --build ./ && make install
ENV PYTHONPATH=/opt/pcraster36/python

COPY requirements.txt /
RUN python3.6 -m pip install -r /requirements.txt

WORKDIR /
COPY src/lisflood/. /lisflood/
COPY src/lisf1.py /
COPY src/settings_tpl.xml /
COPY LICENSE /
COPY docker-entrypoint.sh /

WORKDIR /lisflood/hydrological_modules
RUN python3.6 compile_kinematic_wave_parallel_tools.py build_ext --inplace

COPY tests/. /tests/

WORKDIR /
COPY pytest.ini /tests
RUN python3.6 -m pytest /tests -x -l -ra

ENTRYPOINT ["/docker-entrypoint.sh"]
