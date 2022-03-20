#
# docker image to test script
# script is copied to /usr/local/azure-ad-user-to-linux
# based on the official rhel ubi images
#

FROM registry.access.redhat.com/ubi8/ubi-init

ADD . /usr/local/azure-ad-user-to-linux/
RUN yum install -y python3 \
    && python3 -m venv /usr/local/azure-ad-user-to-linux/venv \
    && /usr/local/azure-ad-user-to-linux/venv/bin/pip3 install --upgrade pip \
    && /usr/local/azure-ad-user-to-linux/venv/bin/pip3 install -r \
      /usr/local/azure-ad-user-to-linux/requirements.txt \
    && chmod +x \
      /usr/local/azure-ad-user-to-linux/azure-ad-user-to-linux.py \
      /usr/local/azure-ad-user-to-linux/azure-ad-user-to-linux.sh
