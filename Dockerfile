FROM python:3-slim AS builder
ADD . /app
WORKDIR /app

# We are installing a dependency here directly into our app source dir
RUN apt-get update \
&& apt-get install -y git

RUN pip install --target=/app gitpython
RUN pip install --target=/app PyYAML

ENV PYTHONPATH /app
CMD ["/app/main.py"]