"""
Check available methods in MCP ClientSession
"""

from mcp import ClientSession
import inspect

print("=" * 80)
print("MCP ClientSession - Available Public Methods")
print("=" * 80)

# Get all public methods (not starting with _)
public_methods = [m for m in dir(ClientSession) if not m.startswith('_')]

print(f"\nTotal public methods: {len(public_methods)}\n")

# Categorize methods
tool_methods = []
resource_methods = []
prompt_methods = []
server_methods = []
other_methods = []

for method in public_methods:
    if 'tool' in method.lower():
        tool_methods.append(method)
    elif 'resource' in method.lower():
        resource_methods.append(method)
    elif 'prompt' in method.lower():
        prompt_methods.append(method)
    elif method in ['initialize', 'get_server_capabilities', 'send_ping', 'set_logging_level']:
        server_methods.append(method)
    else:
        other_methods.append(method)

def print_method(method_name):
    """Print method with signature"""
    attr = getattr(ClientSession, method_name)
    if callable(attr):
        try:
            sig = inspect.signature(attr)
            # Get return type
            return_annotation = sig.return_annotation
            if return_annotation != inspect.Signature.empty:
                return_type = str(return_annotation).replace('mcp.types.', '')
                print(f"  - {method_name}{sig}")
                print(f"    Returns: {return_type}")
            else:
                print(f"  - {method_name}{sig}")
        except:
            print(f"  - {method_name}(...)")
    else:
        print(f"  - {method_name} (property)")
    print()

# Print categorized methods
if tool_methods:
    print("TOOL METHODS:")
    print("-" * 80)
    for method in tool_methods:
        print_method(method)

if resource_methods:
    print("\nRESOURCE METHODS:")
    print("-" * 80)
    for method in resource_methods:
        print_method(method)

if prompt_methods:
    print("\nPROMPT METHODS:")
    print("-" * 80)
    for method in prompt_methods:
        print_method(method)

if server_methods:
    print("\nSERVER METHODS:")
    print("-" * 80)
    for method in server_methods:
        print_method(method)

if other_methods:
    print("\nOTHER METHODS:")
    print("-" * 80)
    for method in other_methods:
        print_method(method)

print("=" * 80)

