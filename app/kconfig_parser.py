import os
import re
import glob
import subprocess

def find_kconfig_files(root):
    kconfigs = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f == "Kconfig":
                kconfigs.append(os.path.join(dirpath, f))
    return kconfigs

def parse_kconfig_file(path):
    configs = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    current = None
    in_help = False
    help_lines = []

    for line in lines:
        if line.strip().startswith("config "):
            if current and help_lines:
                current["help"] = " ".join(help_lines).strip()
                configs.append(current)
            current = {
                "symbol": line.strip().split()[1],
                "title": "",
                "help": ""
            }
            in_help = False
            help_lines = []
        elif current and not current["title"] and line.strip().startswith("tristate"):
            current["title"] = line.strip().strip('"')
        elif line.strip() == "help":
            in_help = True
        elif in_help:
            if line.startswith(" ") or line == "\n":
                help_lines.append(line.strip())
            else:
                in_help = False
                if current and help_lines:
                    current["help"] = " ".join(help_lines).strip()
                    configs.append(current)
                current = None
                help_lines = []

    if current and help_lines:
        current["help"] = " ".join(help_lines).strip()
        configs.append(current)

    return configs

def extract_all_configs(root):
    kconfigs = find_kconfig_files(root)
    print(f"DEBUG: Found {len(kconfigs)} Kconfig files in {root}")
    if len(kconfigs) > 0:
        print(f"DEBUG: Sample Kconfig files: {kconfigs[:5]}")
    
    all_configs = []
    for path in kconfigs:
        configs = parse_kconfig_file(path)
        all_configs.extend(configs)
    
    print(f"DEBUG: Total configs parsed: {len(all_configs)}")
    if len(all_configs) > 0:
        print(f"DEBUG: Sample config symbols: {[c['symbol'] for c in all_configs[:5]]}")
    
    return all_configs

def get_module_info_via_modinfo(module_path):
    try:
        if module_path.endswith('.xz'):
            result = subprocess.run(['modinfo', module_path], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('description:'):
                        return line.split(':', 1)[1].strip()
                    
        return None
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return None

def parse_builtin_modinfo(modinfo_path):
    entries = []
    if not os.path.isfile(modinfo_path):
        return entries

    with open(modinfo_path, "r", encoding="utf-8", errors="ignore") as f:
        current = {}
        for line in f:
            line = line.strip()
            if not line:
                if current:
                    entries.append(current)
                    current = {}
                continue
            if ':' in line:
                k, v = line.split(':', 1)
                current[k.strip()] = v.strip()
        if current:
            entries.append(current)
    return entries

def generate_module_index(kconfig_root, modules_root, progress_callback=None):
    if progress_callback:
        progress_callback("Parsing Kconfig files...", 15)
    
    configs = extract_all_configs(kconfig_root)
    config_map = {c["symbol"].lower(): c for c in configs}
    
    print(f"DEBUG: Found {len(configs)} Kconfig entries")
    print(f"DEBUG: Sample config keys: {list(config_map.keys())[:10]}")

    if progress_callback:
        progress_callback("Scanning module files...", 25)

    module_paths = glob.glob(modules_root + "/**/*.ko*", recursive=True)
    print(f"Found {len(module_paths)} compressed .ko files")

    if progress_callback:
        progress_callback("Loading builtin module info...", 30)

    builtin_info_path = os.path.join(os.path.dirname(modules_root), "modules.builtin.modinfo")
    print(f"DEBUG: Looking for builtin modinfo at: {builtin_info_path}")
    print(f"DEBUG: Builtin modinfo exists: {os.path.exists(builtin_info_path)}")
    
    if not os.path.exists(builtin_info_path):
        alt_paths = [
            os.path.join(os.path.dirname(os.path.dirname(modules_root)), "modules.builtin.modinfo"),
            os.path.join("/run/current-system/kernel-modules/lib/modules", os.path.basename(modules_root.split('/modules/')[1].split('/')[0]), "modules.builtin.modinfo"),
        ]
        for alt_path in alt_paths:
            print(f"DEBUG: Trying alternative path: {alt_path}")
            if os.path.exists(alt_path):
                builtin_info_path = alt_path
                print(f"DEBUG: Found builtin modinfo at alternative path: {builtin_info_path}")
                break
    
    builtin_entries = parse_builtin_modinfo(builtin_info_path)
    print(f"DEBUG: Found {len(builtin_entries)} builtin entries")

    if progress_callback:
        progress_callback("Processing modules...", 35)

    module_index = []
    matched_count = 0
    builtin_matched_count = 0
    modinfo_matched_count = 0
    
    total_modules = len(module_paths)
    for i, path in enumerate(module_paths):
        if progress_callback and i % 100 == 0:
            progress_percent = 35 + int((i / total_modules) * 5)
            progress_callback(f"Processing modules... ({i}/{total_modules})", progress_percent)
        
        if i < 5:
            print(f"DEBUG: Processing module {i+1}: {path}")
        
        filename = os.path.basename(path)
        modname = filename.replace(".ko", "").replace(".xz", "").lower()
        
        if i < 5:
            print(f"DEBUG: Module name extracted: '{modname}'")

        matched_config = None
        for key in config_map:
            if modname in key.lower() or key.lower() in modname:
                matched_config = config_map[key]
                matched_count += 1
                if i < 5:
                    print(f"DEBUG: Found Kconfig match for '{modname}': {key}")
                break

        modinfo_entry = next((m for m in builtin_entries if m.get("name", "").lower() == modname), None)
        if modinfo_entry:
            builtin_matched_count += 1
            if i < 5:
                print(f"DEBUG: Found builtin match for '{modname}': {modinfo_entry}")

        desc = "No description found."
        if matched_config:
            desc = matched_config["help"]
        elif modinfo_entry and "description" in modinfo_entry:
            desc = modinfo_entry["description"]
        else:
            modinfo_desc = get_module_info_via_modinfo(path)
            if modinfo_desc:
                desc = modinfo_desc
                modinfo_matched_count += 1
                if i < 5:
                    print(f"DEBUG: Found modinfo description for '{modname}': {modinfo_desc[:50]}...")

        module_index.append({
            "config": matched_config["symbol"] if matched_config else modname,
            "title": matched_config["title"] if matched_config else modname,
            "desc": desc,
            "path": path
        })

    print(f"DEBUG: Kconfig matches: {matched_count}/{len(module_paths)}")
    print(f"DEBUG: Builtin matches: {builtin_matched_count}/{len(module_paths)}")
    print(f"DEBUG: Modinfo matches: {modinfo_matched_count}/{len(module_paths)}")
    print(f"Final indexed modules: {len(module_index)}")
    return module_index
