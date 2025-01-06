#!/bin/bash

wget https://archive.apache.org/dist/maven/maven-3/3.8.6/binaries/apache-maven-3.8.6-bin.tar.gz -P /tmp # for running projects in GHRB benchmark
tar -xzvf /tmp/apache-maven-3.8.6-bin.tar.gz -C /opt

wget https://archive.apache.org/dist/maven/maven-4/4.0.0-beta-4/binaries/apache-maven-4.0.0-beta-4-bin.tar.gz -P /tmp
tar -xzvf /tmp/apache-maven-4.0.0-beta-4-bin.tar.gz -C /opt

git config --global --add safe.directory '*'

update-alternatives --set java /usr/lib/jvm/java-17-openjdk-amd64/bin/java
source /root/data/GHRB/set_env.sh

pip install gdown 
# pip install -U sentence-transformers nltk
apt install nano
apt-get install zip