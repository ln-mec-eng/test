import os
import re

directory_path = os.path.join(os.path.dirname(__file__), 'sass')
bridge_tokens_path = os.path.join(os.path.dirname(__file__), 'sass', 'libs', '_bridge-tokens.scss')

# 1. Gather all unique variables
# regex explicitly looks for var(--_ emojis ...)
regex = re.compile(r'var\(--_?[🎨🔠🔘📏]-?([^\)]+)\)')
unique_vars = set()

def walk_dir(dir_path):
    files_list = []
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.scss'):
                files_list.append(os.path.join(root, file))
    return files_list

# Pass 1: Find all variables
scss_files = walk_dir(directory_path)

for file_path in scss_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Find all raw full matches (e.g. var(--_🎨-...))
        # re.finditer is better to get the exact matched string
        for match in re.finditer(r'var\(--_?[🎨🔠🔘📏]-?[^\)]+\)', content):
            unique_vars.add(match.group(0))


# 2. Generate new names
var_map = {} # original -> {fullInnerVar, scssVarName}

for original_var_call in unique_vars:
    # Extract the inner variable name
    # e.g. --_🎨-color--tokens---button-secondary-default--text
    inner_var_match = re.search(r'var\((--_?[🎨🔠🔘📏]-?([^\)]+))\)', original_var_call)
    if inner_var_match:
        full_inner_var = inner_var_match.group(1) # --_🎨-color--tokens---button-secondary...
        clean_name = inner_var_match.group(2) # color--tokens---button-secondary...
        
        # Clean up the name to make it a nice SCSS variable
        clean_name = re.sub(r'---+', '-', clean_name)
        clean_name = re.sub(r'--+', '-', clean_name)
        
        # Remove redundant prefixes if they exist
        clean_name = re.sub(r'^color-tokens-', 'color-', clean_name)
        clean_name = re.sub(r'^typography-', '', clean_name)
        
        # Remove any trailing dashes
        clean_name = re.sub(r'-$', '', clean_name)
        
        # Create the SCSS variable name
        scss_var_name = f"${clean_name}"
        
        var_map[original_var_call] = {
            'fullInnerVar': full_inner_var,
            'scssVarName': scss_var_name
        }

# 3. Generate _bridge-tokens.scss content
bridge_content = """// --------------------------------------------------------
// Theme Configuration (Overrides)
// --------------------------------------------------------
// Altere os valores abaixo de `null` para a sua cor/tamanho desejado
// para sobrescrever as propriedades correspondentes na raiz da biblioteca.

"""

# Sort variables for better readability in the generated file
sorted_vars = sorted(var_map.values(), key=lambda x: x['scssVarName'])

for v in sorted_vars:
    custom_name = v['scssVarName'].replace('$', '$custom-')
    bridge_content += custom_name + ": null !default;\n"

bridge_content += "\n:root {\n"
for v in sorted_vars:
    custom_name = v['scssVarName'].replace('$', '$custom-')
    bridge_content += "  @if " + custom_name + " { " + v['fullInnerVar'] + ": #{" + custom_name + "}; }\n"
bridge_content += "}\n\n"

bridge_content += """// --------------------------------------------------------
// Bridge Tokens
// --------------------------------------------------------
// Nomes amigáveis mapeados de volta para as CSS variables ativas.

"""

for v in sorted_vars:
    bridge_content += f"{v['scssVarName']}: var({v['fullInnerVar']});\n"

# Write _bridge-tokens.scss
with open(bridge_tokens_path, 'w', encoding='utf-8') as f:
    f.write(bridge_content)
    
print(f"Generated {bridge_tokens_path} with {len(sorted_vars)} variables.")


# 4. Replace in all SCSS files
files_modified = 0

for file_path in scss_files:
    if file_path == bridge_tokens_path:
        continue # Skip the bridge tokens file itself during replacement
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original_content = content
    
    # Replace longer strings first to prevent partial replacements 
    # (e.g. if var(--a) and var(--a-b) exist, replacing var(--a) first breaks var(--a-b))
    sorted_keys = sorted(var_map.keys(), key=len, reverse=True)
    
    for key in sorted_keys:
        value_data = var_map[key]
        # Literal string replacement since there's no regex logic needed for the exact string
        content = content.replace(key, value_data['scssVarName'])
        
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        files_modified += 1
        print(f"Updated {file_path}")

print(f"\nFinished! Modified {files_modified} files.")
