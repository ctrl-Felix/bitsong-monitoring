FROM python:3.9-alpine
WORKDIR /api
COPY ./requirements.txt /api/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /api/requirements.txt
COPY ./api /api/api
COPY ./database /api/database
CMD python -m api