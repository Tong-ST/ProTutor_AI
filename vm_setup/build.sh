#!/bin/bash

sudo apt update
sudo apt install-y docker.io python3-pip

pip install fastapi uvicorn

# if have docker permission run command below and logout/login
# sudo usermod -aG docker $USER

sudo systemctl enable docker
sudo systemctlstart docker

docker pull python:3.11

docker build-t sandbox-python .

cp executor.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable executor.service
sudo systemctl start executor.service
