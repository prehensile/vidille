FROM python:3.7-alpine

LABEL maintainer="Henry Cooke <me@prehensile.co.uk>"
LABEL verion="0.1"
LABEL description="vidille Telnet Server"

RUN apk upgrade --update &&  \
    apk add git ffmpeg-dev zlib-dev jpeg-dev pkgconfig build-base

COPY media/rick.mp4 /opt/vidille/media/
COPY requirements.txt /opt/vidille/
WORKDIR /opt/vidille
RUN pip install -r requirements.txt

COPY vidille.py /opt/vidille/
COPY config.py /opt/vidille/
COPY server.py /opt/vidille/

EXPOSE 2020
ENTRYPOINT ["python", "server.py" ]
