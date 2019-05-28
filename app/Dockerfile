FROM python:3.7-alpine

COPY . /app

WORKDIR /app

RUN pip install -r reqs.txt

EXPOSE 5000

CMD ["python", "app.py"]
