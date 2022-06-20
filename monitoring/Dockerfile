FROM python:3.9-alpine
WORKDIR /monitoring
COPY ./requirements.txt /monitoring/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /monitoring/requirements.txt
COPY ./monitoring /monitoring/monitoring
COPY ./database /monitoring/database
CMD python -m monitoring