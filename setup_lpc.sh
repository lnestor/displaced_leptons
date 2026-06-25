#!/usr/bin/env bash
# Run once after a fresh clone to set up the LPC apptainer environment.
# Safe to re-run -- idempotent.

set -e

# Download and run the lpcjobqueue bootstrap to create shell and .bashrc.
curl -OL https://raw.githubusercontent.com/PocketCoffea/lpcjobqueue/main/bootstrap.sh
bash bootstrap.sh
rm bootstrap.sh

MARKER="# displaced-leptons setup"

if grep -q "$MARKER" .bashrc 2>/dev/null; then
    echo "Analysis setup already present in .bashrc -- skipping."
else
    cat >> .bashrc << 'EOF'

# displaced-leptons setup
# Create a pocket-coffea wrapper in the venv so it uses the venv Python
# (which has lpcjobqueue) instead of the system Python.
if [[ -d .env ]] && [[ ! -f .env/bin/pocket-coffea ]]; then
    printf '#!/usr/bin/env bash\nexec "$(dirname "$(realpath "${BASH_SOURCE[0]}")")/python" -m pocket_coffea "$@"\n' > .env/bin/pocket-coffea
    chmod +x .env/bin/pocket-coffea
fi
# Install the analysis package in editable mode so local modules are importable.
pip install -e . -q
EOF
    echo "Added analysis setup to .bashrc."
fi

echo "Done. Run ./shell to enter the environment."
