FROM python:3.5-stretch
MAINTAINER Domenico Nappo <domenico.nappo@gmail.com>

ENV no_proxy=jrc.it,localhost,ies.jrc.it,127.0.0.1,jrc.ec.europa.eu
ENV ftp_proxy=http://10.168.209.72:8012
ENV https_proxy=http://10.168.209.72:8012
ENV http_proxy=http://10.168.209.72:8012
ENV DEBIAN_FRONTEND=noninteractive
#ENV PATH=/opt/cmake-3.14.6-Linux-x86_64/bin:/opt/pcraster/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH}
ENV PATH=/opt/pcraster/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH}
ENV PYTHONPATH=/opt/pcraster/python:${PYTHONPATH}
ENV TZ=Europe/RomeB

RUN echo 'Acquire::https::Proxy "http://10.168.209.72:8012";' >> /etc/apt/apt.conf.d/30proxy \
 && echo 'Acquire::http::Proxy "http://10.168.209.72:8012";' >> /etc/apt/apt.conf.d/30proxy

RUN apt-get update && apt-get install -y --no-install-recommends software-properties-common apt-file apt-utils
RUN apt-file update
RUN apt-get install -y --no-install-recommends gcc g++ git cmake \
                    qtbase5-dev libncurses5-dev libqwt-qt5-dev libqt5opengl5-dev libqt5opengl5 \
                    libxerces-c-dev libboost-all-dev libgdal-dev python3-numpy python3-docopt \
  && apt-get clean && apt-get autoremove

WORKDIR /opt
RUN wget -q http://pcraster.geo.uu.nl/pcraster/4.2.1/pcraster-4.2.1.tar.bz2 && \
    tar xf pcraster-4.2.1.tar.bz2 && rm pcraster-4.2.1.tar.bz2 && cd pcraster-4.2.1 && mkdir -p build && \
    mkdir -p /lisflood && mkdir -p /input && mkdir -p /output && mkdir -p /tests && mkdir -p /usecases && mkdir -p /data

COPY requirements.txt /

RUN /usr/local/bin/pip3 install -U pip && /usr/local/bin/pip3 install -r /requirements.txt \
 && cd /usr/lib/x86_64-linux-gnu/ && ln -s libboost_python-py35.so libboost_python3.so

WORKDIR /opt/pcraster-4.2.1/build
RUN cmake -DFERN_BUILD_ALGORITHM:BOOL=TRUE -DCMAKE_INSTALL_PREFIX:PATH=/opt/pcraster -DPYTHON_EXECUTABLE:FILEPATH=/usr/bin/python3.5 ../ \
 && cmake --build ./ && make install

WORKDIR /
COPY LICENSE /
COPY docker-entrypoint.sh /
COPY src/lisflood/. /lisflood/
COPY src/lisf1.py /
COPY src/settings_tpl.xml /lisflood/

WORKDIR /lisflood/hydrological_modules
RUN python3.5 compile_kinematic_wave_parallel_tools.py build_ext --inplace

COPY tests/. /tests/
RUN /usr/local/bin/pip3 install pytest && pytest /tests -s

ENTRYPOINT ["/docker-entrypoint.sh"]
