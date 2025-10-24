#!/usr/bin/env python3

"""
Parses a GFXReconstruct YAML schema and generates Markdown documentation.

Usage:
    python generate_schema_docs.py <input_yaml_file> <output_markdown_file>

Requires:
    PyYAML (install with: pip install PyYAML)
"""

import sys
import yaml
import io

def format_as_yaml_code(data):
    """Formats a Python object as a YAML string inside a Markdown code block."""
    if data is None:
        return ""
    # Dump to a string, remove trailing newlines, and wrap in code fences
    yaml_str = yaml.dump(data, indent=2, sort_keys=False).strip()
    return f"```yaml\n{yaml_str}\n```"

def generate_key_value_table(data):
    """Generates a 2-column Markdown table for a simple dictionary."""
    stream = io.StringIO()
    stream.write("| Property | Value |\n")
    stream.write("| --- | --- |\n")
    for key, value in data.items():
        # Clean up newlines in value strings for table cells
        value_str = str(value).replace("\n", " ")
        stream.write(f"| `{key}` | {value_str} |\n")
    return stream.getvalue()

def generate_external_enums_table(data):
    """Generates a table for the 'external_enums' section."""
    stream = io.StringIO()
    stream.write("| Enum Name | C++ Enum | Headers |\n")
    stream.write("| --- | --- | --- |\n")
    for name, info in data.items():
        headers = ", ".join([f"`{h}`" for h in info.get('headers', [])])
        stream.write(f"| `{name}` | `{info.get('cxx_enum', '')}` | {headers} |\n")
    return stream.getvalue()

def generate_primitives_table(data):
    """Generates a table for the 'primitives' section."""
    stream = io.StringIO()
    stream.write("| Primitive | Size in Bytes | Type |\n")
    stream.write("| --- | --- | --- |\n")
    for name, definition in data.items():
        ty = 'Unknown'
        if 'signed' in definition:
            ty = 'signed int' if definition['signed'] else 'unsigned int'
        else:
            ty = 'float' if 'float' in definition and definition['float'] else 'Unknown'
        stream.write(f"| `{name}` | `{definition['bytes']}` | `{ty}` |\n")
    return stream.getvalue()

def generate_field_kinds_table(data):
    """Generates a table for the 'field_kinds' section."""
    stream = io.StringIO()
    stream.write("| Kind | Definition |\n")
    stream.write("| --- | --- |\n")
    for name, definition in data.items():
        stream.write(f"| `{name}` | {definition.get('description', 'N/A')} |\n")
    return stream.getvalue()

def generate_complex_types_table(data):
    """
    Generates a table for the 'complex_types' section, with a
    nested HTML table for fields.
    """
    stream = io.StringIO()
    stream.write("| Type Name | Fields |\n")
    stream.write("| --- | --- |\n")
    
    for name, definition in data.items():
        # Start the outer table row
        stream.write(f"| **`{name}`** | ")
        
        # Build the HTML sub-table string
        sub_table = io.StringIO()
        # Adding some basic styling to the HTML table
        sub_table.write("<table style=\"border-collapse: collapse; width: 100%;\">")
        sub_table.write("<thead>")
        sub_table.write("<tr style=\"background-color: #f2f2f2;\">")
        sub_table.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Name</th>")
        sub_table.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Type</th>")
        sub_table.write("<th style=\"border: 1px solid #ddd; padding: 8px; text-align: left;\">Count</th>")
        sub_table.write("</tr>")
        sub_table.write("</thead>")
        sub_table.write("<tbody>")
        
        fields = definition.get('fields', [])
        if not fields:
            sub_table.write("<tr><td colspan=\"3\" style=\"border: 1px solid #ddd; padding: 8px;\">(No fields defined)</td></tr>")
        else:
            for field in fields:
                field_name = field.get('name', 'N/A')
                
                # Determine Type string
                field_type_str = field.get('type', 'N/A')
                type_str = ""
                if field_type_str == 'array':
                    element_type = field.get('element', {}).get('type', '?')
                    type_str = f"array (element: <code>{element_type}</code>)"
                elif field_type_str == 'enum':
                    type_str = f"enum (<code>{field.get('enum', '?')}</code>)"
                else:
                    type_str = f"<code>{field_type_str}</code>"
                
                # Determine Count string
                count_str = "1" # Default
                if 'count' in field:
                    count_str = str(field['count'])
                elif 'count_from' in field:
                    count_str = f"from <code>{field['count_from']}</code>"
                elif field_type_str == 'array':
                     if 'count' not in field and 'count_from' not in field:
                         count_str = "N/A"

                sub_table.write("<tr>")
                sub_table.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\"><code>{field_name}</code></td>")
                sub_table.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\">{type_str}</td>")
                sub_table.write(f"<td style=\"border: 1px solid #ddd; padding: 8px;\"><code>{count_str}</code></td>")
                sub_table.write("</tr>")

        sub_table.write("</tbody></table>")

        # Get the HTML sub-table string. No need to replace newlines.
        sub_table_str = sub_table.getvalue()
        stream.write(f"{sub_table_str} |\n")
        
    return stream.getvalue()

def generate_levels_table(data):
    """Generates a table for the 'levels' section."""
    stream = io.StringIO()
    stream.write("| Name | Handled By |\n")
    stream.write("| --- | --- |\n")
    for level in data:
        stream.write(f"| `{level.get('name')}` | `{level.get('handled_by')}` |\n")
    return stream.getvalue()

def generate_blocks_table(data):
    """Generates a table for the 'blocks' section, as requested."""
    stream = io.StringIO()
    # Note: "Payload" and "Dispatch" are complex and will be embedded as
    # YAML code blocks within the table cells for readability.
    stream.write("| Name | Block Type | Payload / Variants | Dispatch |\n")
    stream.write("| --- | --- | --- | --- |\n")
    
    for block in data:
        name = block.get('name', 'N/A')
        block_type = block.get('block_type', 'N/A')
        
        # Aggregate payload-like structures (payload, prefix, variants)
        # This handles the special case of 'MetaData' blocks gracefully
        payload_data = {}
        if 'payload' in block:
            payload_data = block['payload']
        else:
            if 'prefix' in block:
                payload_data['prefix'] = block['prefix']
            if 'variants' in block:
                payload_data['variants'] = block['variants']
        
        payload_str = format_as_yaml_code(payload_data)
        dispatch_str = format_as_yaml_code(block.get('dispatch'))
        
        # Write the table row
        # We replace newlines with <br> to ensure the YAML block
        # renders correctly within a single table cell.
        stream.write(
            f"| **{name}** | `{block_type}` "
            f"| {payload_str.replace_control_chars()} "
            f"| {dispatch_str.replace_control_chars()} |\n"
        )
    return stream.getvalue()

def generate_documentation(schema_data):
    """Generates the full Markdown documentation string from the parsed schema."""
    
    # Simple helper to replace newlines in our code blocks for table compatibility
    class SafeStr(str):
        def replace_control_chars(self):
            return self.replace("\n", "<br>")

    # Monkey-patch the str class for this function's scope
    # (This is a bit of a hack, but avoids passing wrappers everywhere)
    global format_as_yaml_code
    _original_format_as_yaml_code = format_as_yaml_code
    def safe_format_as_yaml_code(data):
        return SafeStr(_original_format_as_yaml_code(data))
    format_as_yaml_code = safe_format_as_yaml_code
    
    stream = io.StringIO()
    
    # --- Title ---
    schema_name = schema_data.get('schema', {}).get('name', 'Schema')
    schema_version = schema_data.get('schema', {}).get('version', '')
    stream.write(f"# {schema_name.capitalize()} Schema Documentation (v{schema_version})\n\n")

    # --- Table Generators Mapping ---
    # Maps top-level YAML keys to their specific table-generating function
    generators = {
        'schema': ("Schema Properties", generate_key_value_table),
        'external_enums': ("External Enums", generate_external_enums_table),
        'primitives': ("Primitives", generate_primitives_table),
        'field_kinds': ("Special field types with complex decoding logic", generate_field_kinds_table),
        'complex_types': ("Complex Types (Structs)", generate_complex_types_table),
        'block_header': ("Block Header", generate_key_value_table),
        'levels': ("Decoding Levels", generate_levels_table),
        'blocks': ("Block Payloads", generate_blocks_table),
    }

    # --- Generate Sections ---
    for key, (title, func) in generators.items():
        if key in schema_data:
            stream.write(f"## {title}\n\n")
            stream.write(func(schema_data[key]))
            stream.write("\n\n---\n\n")
            
    # Restore original function
    format_as_yaml_code = _original_format_as_yaml_code
    return stream.getvalue()

def main():
    """Main script entry point."""
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_yaml> <output_markdown>", file=sys.stderr)
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print(f"Loading schema from '{input_file}'...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            schema_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while reading the file: {e}", file=sys.stderr)
        sys.exit(1)

    print("Generating Markdown documentation...")
    try:
        markdown_content = generate_documentation(schema_data)
    except Exception as e:
        print(f"An unexpected error occurred during documentation generation: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Writing documentation to '{output_file}'...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
    except IOError as e:
        print(f"Error writing to output file: {e}", file=sys.stderr)
        sys.exit(1)
        
    print("Done.")

if __name__ == "__main__":
    main()
