FROM python:3.11

RUN mkdir -p /ssdl
ADD . /ssdl
WORKDIR /ssdl

RUN pip install -r requirements.txt

CMD ["bash"]
