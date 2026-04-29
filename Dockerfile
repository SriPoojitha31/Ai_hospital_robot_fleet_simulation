FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

COPY hospital_ws /workspace/hospital_ws

RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install scipy networkx scikit-learn joblib pyyaml flask prometheus-client pytest

CMD ["/bin/bash", "-lc", "source /opt/ros/jazzy/setup.bash && cd /workspace/hospital_ws && bash run_all.sh"]
