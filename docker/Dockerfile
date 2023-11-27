# Cellprofiler docker registry

FROM cellprofiler/cellprofiler:4.2.4

# Install 

RUN apt-get -y update           && \
    apt-get -y upgrade          && \
    apt-get -y install 		

WORKDIR /usr/local/src

# Install AWS CLI

RUN python3.8 -m pip install awscli 

# Install boto3

RUN python3.8 -m pip install boto3

# Install watchtower for logging

RUN python3.8 -m pip install watchtower

# Install pandas for optional file downloading

RUN python3.8 -m pip install pandas

# SETUP NEW ENTRYPOINT

RUN mkdir -p /home/ubuntu/
WORKDIR /home/ubuntu

COPY run-worker.sh .
RUN chmod 755 run-worker.sh


WORKDIR /home/ubuntu
ENTRYPOINT ["./run-worker.sh"]
CMD [""]

