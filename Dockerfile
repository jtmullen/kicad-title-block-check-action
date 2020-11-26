FROM alpine:3.10

COPY main.py /main.py

RUN apk --no-cache add git
RUN apk add python3
RUN apk add py3-pip
RUN pip3 install gitpython
RUN pip3 install PyYAML
RUN git clone https://github.com/realthunder/kicad_parser.git \
&& cd kicad_parser \
&& git checkout 5ec854b3119071b1b56ad534900f495a91ba6a09 \
&& git submodule update --init

CMD ["/main.py"]
ENTRYPOINT ["python3"]