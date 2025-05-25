# ベースイメージに python:3.13-slim を指定
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        libopenblas-dev \
        liblapack-dev && \
    rm -rf /var/lib/apt/lists/*

    RUN pip install --no-cache-dir \
        numpy \
        pandas \
        scipy \
        matplotlib \
        seaborn \
        pillow \
        opencv-python-headless \
        japanize-matplotlib \
        openpyxl \
        requests \
        scikit-learn \
        plotly \
        python-docx \
        beautifulsoup4
    
WORKDIR /workspace

CMD ["bash"]