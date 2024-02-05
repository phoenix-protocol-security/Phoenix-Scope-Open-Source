FROM python:3-slim

# Install Essentials
RUN apt update && \
    apt upgrade && \
    apt-get install -y build-essential libpcap-dev && \
    apt install -y git

RUN mkdir /app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
