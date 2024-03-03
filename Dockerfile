FROM python:3.11

RUN mkdir -p /ssdl
COPY requirements.txt /ssdl/requirements.txt
WORKDIR /ssdl
RUN pip install -r requirements.txt

ADD . /ssdl

RUN pip install .

CMD ["bash"]
