import subprocess
import sys


def _parse_xrootd_url(url):
    """Return (server, path) from a root://server//path URL."""
    rest = url[len("root://"):]
    slash = rest.index("/")
    server = "root://" + rest[:slash]
    path = "/" + rest[slash:].lstrip("/")
    return server, path


def get_root_files(eos_dir, recursive=False):
    """List .root files in an EOS xrootd directory."""
    server, path = _parse_xrootd_url(eos_dir)

    if recursive:
        result = subprocess.run(
            ["xrdfs", server, "ls", "-R", path], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR: xrdfs ls -R failed:\n{result.stderr.strip()}")
            sys.exit(1)
        return [f"{server}/{line.strip()}" for line in result.stdout.splitlines() if line.strip().endswith(".root")]

    result = subprocess.run(["xrdfs", server, "ls", path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: xrdfs ls failed:\n{result.stderr.strip()}")
        sys.exit(1)
    return [f"{server}/{line.strip()}" for line in result.stdout.splitlines() if line.strip().endswith(".root")]


def list_dir_entries(eos_dir):
    """List immediate entries (files and subdirs) of an EOS xrootd directory.
    Returns None instead of exiting if the directory doesn't exist."""
    server, path = _parse_xrootd_url(eos_dir)
    result = subprocess.run(["xrdfs", server, "ls", path], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return [f"{server}/{line.strip()}" for line in result.stdout.splitlines() if line.strip()]


def try_get_root_files(eos_dir, recursive=False):
    """Like get_root_files, but returns None instead of exiting when the
    directory doesn't exist or the listing otherwise fails."""
    server, path = _parse_xrootd_url(eos_dir)
    args = ["xrdfs", server, "ls"]
    if recursive:
        args.append("-R")
    args.append(path)
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return [f"{server}/{line.strip()}" for line in result.stdout.splitlines() if line.strip().endswith(".root")]


def get_file_size(xrootd_path):
    """Get file size in bytes using xrdfs stat."""
    server, path = _parse_xrootd_url(xrootd_path)
    result = subprocess.run(["xrdfs", server, "stat", path], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if "Size:" in line:
            return int(line.split("Size:")[1].strip().split()[0])
    return 0
