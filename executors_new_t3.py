import os
import socket
from coffea import processor as coffea_processor
from pocket_coffea.executors.executors_base import ExecutorFactoryABC
from pocket_coffea.executors.executors_base import IterativeExecutorFactory, FuturesExecutorFactory
from pocket_coffea.parameters.dask_env import setup_dask
from dask_jobqueue import HTCondorCluster
from distributed import Client


def get_worker_env(x509_path, run_options):
    env_worker = [
        'export XRD_RUNFORKHANDLER=1',
        'export MALLOC_TRIM_THRESHOLD_=0',
    ]
    if not run_options['ignore-grid-certificate']:
        proxy_filename = os.path.basename(x509_path)
        # Proxy delivered via HTCondor transfer_input_files into _CONDOR_SCRATCH_DIR
        env_worker.append(f'export X509_USER_PROXY=$_CONDOR_SCRATCH_DIR/{proxy_filename}')
    if run_options.get('custom-setup-commands'):
        env_worker += run_options['custom-setup-commands']
    return env_worker


class DaskExecutorFactory(ExecutorFactoryABC):

    def __init__(self, run_options, outputdir, **kwargs):
        self.outputdir = outputdir
        super().__init__(run_options, **kwargs)

    def setup(self):
        self.setup_proxyfile()
        import dask.config
        setup_dask(dask.config)

        log_folder = 'condor_log'
        log_dir = f'{self.outputdir}/{log_folder}'
        os.makedirs(log_dir, exist_ok=True)

        # Use IP — interactive-0-0.localdomain may not resolve from worker nodes
        scheduler_host = socket.gethostbyname(socket.gethostname())

        x509_path = getattr(self, 'x509_path', None)

        job_extra = {
            'universe': 'container',
            'container_image': self.run_options.get('worker-image', '/home/lnestor/scratch0/pocketcoffea-lxplus-el9-latest.sif'),
            'container_mount_points': '/cvmfs',
            'log': f'{log_dir}/dask_job_output.log',
            'output': f'{log_dir}/dask_job_output.out',
            'error': f'{log_dir}/dask_job_output.err',
        }
        if not self.run_options.get('ignore-grid-certificate', False) and x509_path:
            # HTCondor copies this file to _CONDOR_SCRATCH_DIR on the worker,
            # which is visible inside the container. get_worker_env sets X509_USER_PROXY there.
            job_extra['transfer_input_files'] = x509_path
            print(f'>> Transferring proxy {x509_path} to workers via HTCondor file transfer')

        print(f'>> Creating HTCondorCluster, scheduler on {scheduler_host}')
        self.dask_cluster = HTCondorCluster(
            cores=self.run_options.get('cores-per-worker', 1),
            memory=self.run_options.get('mem-per-worker', '4GB'),
            disk=self.run_options.get('disk-per-worker', '2GB'),
            log_directory=log_dir,
            scheduler_options={
                'host': scheduler_host,
                'dashboard_address': ':8787',
            },
            job_script_prologue=get_worker_env(x509_path, self.run_options),
            job_extra_directives=job_extra,
        )

        print('>> Sending out jobs')
        self.dask_cluster.scale(jobs=self.run_options['scaleout'])

        self.dask_client = Client(self.dask_cluster)
        print('>> Waiting for the first worker to start...')
        self.dask_client.wait_for_workers(1)
        print('>> You can connect to the Dask viewer at http://localhost:8787')

    def get(self):
        return coffea_processor.dask_executor(**self.customized_args())

    def customized_args(self):
        args = super().customized_args()
        args['client'] = self.dask_client
        args['treereduction'] = self.run_options['tree-reduction']
        args['retries'] = self.run_options['retries']
        return args

    def close(self):
        self.dask_client.close()
        self.dask_cluster.close()


def get_executor_factory(executor_name, **kwargs):
    if executor_name == 'iterative':
        return IterativeExecutorFactory(**kwargs)
    elif executor_name == 'futures':
        return FuturesExecutorFactory(**kwargs)
    elif executor_name == 'dask':
        return DaskExecutorFactory(**kwargs)
    else:
        raise NotImplementedError(f'Executor {executor_name} not implemented')
