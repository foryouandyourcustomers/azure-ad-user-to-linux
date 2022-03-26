#
# docker image to test script
# script is copied to /usr/local/azure-ad-user-to-linux
# based on the official rhel ubi images
#

FROM registry.access.redhat.com/ubi8/ubi-init

# install python and ssh, sudo is just used to allow testing all
# setup instructions in the readme
RUN yum install -y openssh-server openssh-clients python3 sudo \
    && systemctl enable sshd \
    && ssh-keygen -A

CMD [ "/sbin/init" ]