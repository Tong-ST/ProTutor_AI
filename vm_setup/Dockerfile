FROM python:3.11-slim

RUN useradd -m sandboxuser

WORKDIR /app

USER sandboxuser

RUN pip install numpy pandas
