FROM python:3.9
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt /code/
RUN apt update && apt -qy upgrade && pip install -r requirements.txt
RUN apt-get update && apt-get install -y postgresql-client
COPY . /code/