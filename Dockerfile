FROM python:3.9
ENV PYTHONUNBUFFERED=1
WORKDIR /code
COPY requirements.txt /code/
RUN apt update && apt -qy upgrade
RUN pip install -r requirements.txt
COPY . /code/