import os
import glob
import subprocess


def get_kernel_module_paths():
    kernel_version = os.uname().release
    nixos_path = (
        f"/run/current-system/kernel-modules/lib/modules/{kernel_version}/kernel"
    )
    fallback_path = f"/lib/modules/{kernel_version}/kernel"

    if os.path.exists(nixos_path):
        base_path = nixos_path
    elif os.path.exists(fallback_path):
        base_path = fallback_path
    else:
        raise RuntimeError("No kernel modules path found.")

    return glob.glob(base_path + "/**/*.ko*", recursive=True)


def extract_module_info(path):
    try:
        output = subprocess.check_output(["modinfo", path], text=True)
        lines = output.splitlines()
        name, desc = None, None
        for line in lines:
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                desc = line.split(":", 1)[1].strip()
        if name and desc:
            return {"name": name, "desc": desc, "path": path}
    except subprocess.CalledProcessError:
        pass
    return None


def get_all_modules():
    paths = get_kernel_module_paths()
    return [mod for path in paths if (mod := extract_module_info(path))]
