FROM ubuntu:18.04

ENV TZ="Europe/Rome"
ENV DEBIAN_FRONTEND="noninteractive"

RUN apt-get update -y && apt-get install apt-utils -y && apt-get install software-properties-common curl wget locales libssl1.0-dev -y && locale-gen en_US.UTF-8

# Ubuntugis unstable repository

RUN add-apt-repository ppa:ubuntugis/ubuntugis-unstable -y && apt-get update && apt-get upgrade -y
# Install specific packages from repository (if a package has been specified)
 

# Install APT package(s) 
ADD apt_install_req.txt /root/
RUN apt-get update && apt-get install -y   $(cat /root/apt_install_req.txt)
RUN apt-get update && apt-get upgrade -y

# Downloading python2 libraries with pip2
ADD requirements.txt /root/
RUN pip2 install --upgrade pip
RUN pip2 install -r /root/requirements.txt

# Downloading python2 libraries with pip2
ADD requirements2.txt /root/
RUN pip2 install --upgrade pip
RUN pip2 install -r /root/requirements2.txt

# Python 2 PCRASTER 4.1.0 installation
RUN apt-get install -y libjpeg62
RUN cd /opt/ && wget -nv http://downloads.sourceforge.net/project/pcraster/PCRaster/4.1.0/pcraster-4.1.0_x86-64.tar.gz
RUN cd /opt/ && tar xzf pcraster-4.1.0_x86-64.tar.gz && rm pcraster-4.1.0_x86-64.tar.gz
# Remove old libexpat
RUN rm /opt/pcraster-4.1.0_x86-64/lib/libexpat.so.1
ENV PYTHONPATH="/opt/pcraster-4.1.0_x86-64/python:${PYTHONPATH}"
ENV PATH="/opt/pcraster-4.1.0_x86-64/bin:${PATH}"

# cdo 1.9.5  Installation
RUN cd /usr/local/src/ && wget -nv https://code.mpimet.mpg.de/attachments/download/18264/cdo-1.9.5.tar.gz && tar -xzf cdo-1.9.5.tar.gz
RUN cd /usr/local/src/cdo-1.9.5 && ./configure --with-netcdf && make -j2 && make install && make clean && cd /

# ECWF Python API
RUN pip install https://software.ecmwf.int/wiki/download/attachments/56664858/ecmwf-api-client-python.tgz

# Cleanup installation files
RUN cd / && rm -fr /root/.cache && rm -rf /var/lib/apt/lists/*

ADD Lisflood /opt/Lisflood
RUN cd /opt/Lisflood/hydrological_modules && python compile_kinematic_wave_parallel_tools.py build_ext --inplace && cd ..

ENTRYPOINT ["python2", "/opt/Lisflood/lisf1.py"]
