import os
from app.kconfig_parser import generate_module_index

def get_all_modules(progress_callback=None):
    kernel_version = os.uname().release

    nixos_path = f"/run/current-system/kernel-modules/lib/modules/{kernel_version}/kernel"
    fallback_path = f"/lib/modules/{kernel_version}/kernel"

    if os.path.exists(nixos_path):
        modules_root = nixos_path
    elif os.path.exists(fallback_path):
        modules_root = fallback_path
    else:
        raise RuntimeError("No kernel module tree found.")

    kconfig_root = os.path.realpath("./linux-src-dev")
    if not os.path.isdir(kconfig_root):
        modules_source_path = f"/run/current-system/kernel-modules/lib/modules/{kernel_version}/source"
        if os.path.isdir(modules_source_path):
            kconfig_root = modules_source_path
        else:
            raise RuntimeError(f"Expected kernel source in ./linux-src-dev or {modules_source_path}. Please run `nix build nixpkgs#linux.dev --impure -o linux-src-dev`")

    print(f"Scanning modules from: {modules_root}")
    print(f"Kconfig root: {kconfig_root}")
    print(f"DEBUG: Checking if kconfig_root exists: {os.path.isdir(kconfig_root)}")

    if not os.path.isdir(kconfig_root):
        raise RuntimeError("Expected kernel source in ./linux-src. Please run `nix build nixpkgs#linux.dev --impure -o linux-src`")

    return generate_module_index(kconfig_root, modules_root, progress_callback)