from fire import Fire

from . import job, vast


def cli():
    Fire({"login": vast.login, "job": job.run_all})


if __name__ == "__main__":
    cli()
