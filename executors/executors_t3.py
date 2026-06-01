from pocket_coffea.executors.executors_base import ExecutorFactoryABC
from dask_jobqueue import HTCondorCluster
from distributed import Client
import os

def get_worker_env(x509_path):
    """Setup environment for workers"""
    env_worker = [
        'export XRD_RUNFORKHANDLER=1',
        'export XRD_REDIRECTLIMIT=255',
        'export MALLOC_TRIM_THRESHOLD_=0',
        f'export X509_USER_PROXY={x509_path}',
        f'export PATH=/share/scratch0/lnestor/micromamba/envs/pocket-coffea/bin:$PATH',
    ]
    return env_worker

class DaskExecutorFactory(ExecutorFactoryABC):
    def __init__(self, run_options, **kwargs):
        # This calls setup() which calls setup_proxyfile()
        super().__init__(run_options, **kwargs)

    def setup(self):
        # Call parent setup which handles proxy copying
        super().setup()

        # Now setup dask cluster
        self.dask_cluster = HTCondorCluster(
            cores=1,
            memory="4GB",
            disk="2GB",
            log_directory="/share/scratch0/lnestor/dask-logs",
            scheduler_options={
                "host": "10.1.255.251",
                "dashboard_address": ":8787"
            },
            env_extra=get_worker_env(self.x509_path),  # Use env_extra, not job_script_prologue
        )

        self.dask_cluster.scale(jobs=80)
        self.dask_client = Client(self.dask_cluster)
        print(f"Dask dashboard: {self.dask_client.dashboard_link}")

    def get(self):
        from coffea.processor import dask_executor
        return dask_executor(client=self.dask_client, status=True, retries=self.run_options.get("retries", 10))

    def close(self):
        self.dask_client.close()
        self.dask_cluster.close()

def get_executor_factory(executor_name, **kwargs):
    if executor_name == "dask":
        return DaskExecutorFactory(**kwargs)
    else:
        raise NotImplementedError(f"Executor {executor_name} not implemented")
