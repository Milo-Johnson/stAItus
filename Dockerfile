FROM python:3.9-alpine
COPY . /staitus
WORKDIR /staitus
RUN pip install -r requirements.txt 
CMD python ./main.py