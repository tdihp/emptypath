FROM python:3-slim

WORKDIR /usr/src/app

COPY . .
RUN pip install -r requirements.txt

CMD ["python", "-m", "emptypath"]
