import os
from typing import *
import stat
import time

import paramiko
import paramiko.util
from tqdm import tqdm
import yaml
from pydantic import BaseModel

from . import vast
from .logger import set_logger

logger = set_logger(__name__)


class InstanceConfig(BaseModel):
    image: str
    disk: int
    setup: str


class Job(BaseModel):
    files: list
    script: str


def sftp_get(sftp: paramiko.SFTPClient, src: str, dst: str):
    if sftp.stat(src).st_mode & stat.S_IFDIR:
        os.makedirs(dst, exist_ok=True)
        for f in sftp.listdir(src):
            sftp_get(
                sftp,
                os.path.join(src, f).replace(os.sep, "/"),
                os.path.join(dst, f).replace(os.sep, "/"),
            )
    else:
        progress = tqdm(total=os.stat(src).st_size, unit="B", unit_scale=True)

        def callback(current, total):
            progress.update(current - progress.n)

        sftp.get(src, dst, callback=callback)


def sftp_put(sftp: paramiko.SFTPClient, src: str, dst: str):
    if os.path.isdir(src):
        sftp.mkdir(dst)
        for f in os.listdir(src):
            sftp_put(
                sftp,
                os.path.join(src, f).replace(os.sep, "/"),
                os.path.join(dst, f).replace(os.sep, "/"),
            )
    else:
        progress = tqdm(total=os.stat(src).st_size, unit="B", unit_scale=True)

        def callback(current, total):
            progress.update(current - progress.n)

        sftp.put(src, dst, callback=callback)


def wait_for_instance(id: int):
    logger.info(f"Waiting for instance {id} to start")
    retry = 0
    while True:
        if retry > 10:
            raise Exception("Timeout waiting for instance to start")
        try:
            instances = vast.get_instances()
        except:
            retry += 1
            time.sleep(10)
            continue
        instance = [i for i in instances if i["id"] == id]
        if len(instance) == 0:
            retry += 1
            time.sleep(10)
            continue
        instance = instance[0]
        if instance["actual_status"] == "running":
            break
        time.sleep(10)

    return instance


def get_ssh_info(instance: Dict[str, Any]):
    ports = instance.get("ports", {})
    port_22d = ports.get("22/tcp", None)
    if port_22d is not None:
        ip = instance["public_ipaddr"]
        port = port_22d[0]["HostPort"]
    else:
        ip = instance["ssh_host"]
        port = int(instance["ssh_port"]) + 1
    return ip, port


def exec_command(client: paramiko.SSHClient, command: str):
    stdin, stdout, stderr = client.exec_command(command)
    while True:
        stdout_line = stdout.readline()
        stderr_line = stderr.readline()
        if not stdout_line and not stderr_line:
            break
        if stdout_line != "":
            print(stdout_line, end="")
        if stderr_line != "":
            print(stderr_line, end="")


def run_job(client: paramiko.SSHClient, job: str):
    sftp = client.open_sftp()

    command = ""

    for line in job.split("\n"):
        if line.startswith("@"):
            if command != "":
                exec_command(client, command)
                command = ""

            cmd = line.split(" ")[0].replace("@", "")
            if cmd == "PUT":
                src, dst = line.split(" ")[1:]
                logger.info(f"Uploading {src} to {dst}")
                sftp_put(sftp, src, dst)
            elif cmd == "GET":
                src, dst = line.split(" ")[1:]
                logger.info(f"Downloading {src} to {dst}")
                sftp_get(sftp, src, dst)
        else:
            command += line + "\n"

    if command != "":
        exec_command(client, command)


def run_all(id: str, config_file: str, job_file: str, log_file: str = "./log-{id}.log"):
    vast.check_api_key()
    with open(config_file, "r") as f:
        config = InstanceConfig(**yaml.load(f, Loader=yaml.FullLoader))
    with open(job_file, "r") as f:
        job = f.read()

    instance_info = vast.create_instance(
        id,
        vast.CreateInstanceRequest(
            client_id="me",
            image=config.image,
            disk=config.disk,
            runtype="ssh ssh_direc ssh_proxy",
            onstart="touch /root/.no_auto_tmux",
        ),
    )

    instance_id = instance_info.new_contract

    logger.info(f"Started instance {instance_id}")

    instance = wait_for_instance(instance_id)
    ip, port = get_ssh_info(instance)

    client = paramiko.SSHClient()
    paramiko.util.log_to_file(log_file.format(id=id))
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, port=port, username="root")
    logger.info(f"Connected to instance {instance_id}")

    logger.info("Running setup script")
    _, stdout, stderr = client.exec_command(config.setup)
    while True:
        stdout_line = stdout.readline()
        stderr_line = stderr.readline()
        if not stdout_line and not stderr_line:
            break
        if stdout_line != "":
            print(stdout_line, end="")
        if stderr_line != "":
            print(stderr_line, end="")

    logger.info("Running job script")
    run_job(client, job)

    vast.delete_instance(instance_id)
    logger.info(f"Deleted instance {instance_id}")
