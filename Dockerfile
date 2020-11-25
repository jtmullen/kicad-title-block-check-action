FROM python:3-slim AS builder

# We are installing a dependency here directly into our app source dir
RUN apt-get update \
&& apt-get install -y git

RUN pip install gitpython
RUN pip install PyYAML

ADD main.py /main.py

ENTRYPOINT ["/main.py"]