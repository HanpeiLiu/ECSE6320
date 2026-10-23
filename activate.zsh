# Run with: source ./activate.zsh
# Activate the project Python environment and its locally installed tools.
_ecse_project_dir="${${(%):-%N}:A:h}"
source "$_ecse_project_dir/.venv/bin/activate"
export PATH="$_ecse_project_dir/tools/bin:$PATH"
unset _ecse_project_dir
