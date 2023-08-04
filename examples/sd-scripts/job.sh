@PUT ./config /root/workspace/config
@PUT ./dataset.zip /root/workspace/dataset.zip

eval "$(/root/miniconda/bin/conda shell.bash hook)"

cd /root/workspace

unzip dataset.zip -d dataset
rm dataset.zip

cd config
python -u /root/workspace/sd-scripts/sdxl_train.py --config_file ./config.toml

@GET /root/workspace/config ./config