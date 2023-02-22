FROM python:3.9.13

ENV PYTHONUNBUFFERED 1

# create root directory for our project in the container
RUN mkdir /RESTapi

# Set the working directory to /music_service
WORKDIR /RESTapi

# Copy the current directory contents into the container at /music_service
ADD . /RESTapi/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt