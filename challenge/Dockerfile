FROM python:3.8-slim

# Create app directory
RUN mkdir -p /app
WORKDIR /app

# Bundle app source
COPY . /app

# Install packages
RUN pip install -r requirements.txt
RUN pip install gunicorn

# Set non root user
RUN useradd -c 'BSidesTLV user' -m -d /home/bsidestlv -s /bin/bash bsidestlv
RUN chown -R bsidestlv:bsidestlv /home/bsidestlv
RUN chown -R bsidestlv:bsidestlv /app

# Allow Port 80/443
RUN apt-get update && apt-get install -y libcap2-bin
RUN setcap CAP_NET_BIND_SERVICE=+eip /usr/local/bin/python3.8

USER bsidestlv
ENV HOME /home/bsidestlv

#EXPOSE 443
#CMD [ "gunicorn", "-b", "0.0.0.0:443", "-w", "2", "--certfile", "/app/ssl/mydomain.com.crt", "--keyfile", "/app/ssl/mydomain.com.key", "index:app" ]

EXPOSE 80
CMD [ "gunicorn", "-b", "0.0.0.0:80", "-w", "2", "index:app" ]
