FROM alpine:3.10

RUN ls

COPY main.py /main.py

RUN ls
RUN apk --no-cache add git
RUN apk add python3
RUN apk add py3-pip
RUN pip3 install gitpython
RUN pip3 install PyYAML
RUN git submodule update --init

CMD ["main.py"]
ENTRYPOINT ["python3"]