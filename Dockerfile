FROM alpine:3.11
ADD . /app
WORKDIR /app

# We are installing a dependency here directly into our app source dir
RUN apk --no-cache add git
RUN apk add python3
RUN apk add py3-pip
RUN pip3 install --target=/app gitpython
RUN pip3 install --target=/app PyYAML



ENV PYTHONPATH /app
CMD ["/app/main.py"]