FROM python:3.7-alpine

LABEL maintainer="Henry Cooke <me@prehensile.co.uk>"
LABEL verion="0.1"
LABEL description="vidille Telnet Server"

RUN apk upgrade --update &&  \
    apk add git ffmpeg-dev zlib-dev jpeg-dev pkgconfig build-base

COPY media/rick.mp4 /opt/vidille/
COPY requirements.txt /opt/vidille/
WORKDIR /opt/vidille
RUN pip install -r requirements.txt

COPY server.py vidille.py /opt/vidille/

RUN mkdir media && mv rick.mp4 media

EXPOSE 2020
ENTRYPOINT ["python", "server.py" ]
