FROM python:3.10-slim
ARG user
ARG password
ADD requirements.lock /
RUN pip install --upgrade --extra-index-url https://$user:$password@distribution.livetech.site -r /requirements.lock
ADD . /loko-cli
ENV PYTHONPATH=$PYTHONPATH:/loko-cli
WORKDIR /loko-cli/loko_cli/services
CMD python services.py
