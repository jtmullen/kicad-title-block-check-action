FROM alpine:3.10

# We are installing a dependency here directly into our app source dir
RUN apk --no-cache add git
RUN apk add python3
RUN apk add py3-pip
RUN pip3 install gitpython
RUN pip3 install PyYAML
RUN git submodule update --init


CMD ["main.py"]
ENTRYPOINT ["python3"]