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
            ["eos", server, "find", "--name", ".*.root", path], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR: eos find failed:\n{result.stderr.strip()}")
            sys.exit(1)
        # eos find returns the physical path under whatever local mount EOS
        # uses (e.g. /eos/uscms), not the logical path used in xrootd URLs --
        # recover the logical path by finding where it reappears in the line.
        files = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            files.append(f"{server}/{line[line.index(path):]}")
        return files

    result = subprocess.run(["xrdfs", server, "ls", path], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: xrdfs ls failed:\n{result.stderr.strip()}")
        sys.exit(1)
    return [f"{server}/{line.strip()}" for line in result.stdout.splitlines() if line.strip().endswith(".root")]


def get_file_size(xrootd_path):
    """Get file size in bytes using xrdfs stat."""
    server, path = _parse_xrootd_url(xrootd_path)
    result = subprocess.run(["xrdfs", server, "stat", path], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if "Size:" in line:
            return int(line.split("Size:")[1].strip().split()[0])
    return 0
