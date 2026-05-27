import subprocess
import sys

def get_crab_output_lfns(task_dir):
    """Run crab getoutput --dump and return a list of output LFNs."""
    result = subprocess.run(
        ["crab", "getoutput", "-d", task_dir, "--dump", "--jobids", "1"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: crab getoutput failed:\n{result.stderr.strip()}")
        sys.exit(1)

    lfns = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("LFN:"):
            lfns.append(line[len("LFN:"):].strip())
    return lfns
