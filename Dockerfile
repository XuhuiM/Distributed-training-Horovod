FROM horovod/horovod:0.19.2-tf2.1.0-torch-mxnet1.6.0-py3.6-gpu
LABEL description="Docker image for Distributed-training-Horovod"
COPY . /root
WORKDIR /root
RUN ls
RUN /usr/bin/python -m pip install --upgrade pip
RUN pip3 install -r requirements.txt 
EXPOSE 8888/tcp
ENV SHELL /bin/bash
ENTRYPOINT ["jupyter", "notebook", "--ip", "0.0.0.0", "--no-browser", "--allow-root"]
