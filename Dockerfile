FROM centos:7

RUN yum install -y epel-release
RUN yum install -y python36
RUN yum install -y python-requests
RUN yum install -y python-jinja2
RUN yum install -y PyYAML
RUN yum install -y git
RUN yum install -y python-pygit2
