import javalang
import os

def mask_method(project_path, old_method_name, new_method_name):
    for root, dirs, files in os.walk(project_path):
        for file in files:
            if file.endswith(".java"):
                with open(os.path.join(root, file), 'r', errors='ignore') as f:
                    code = f.read()
                    codelines = code.split('\n')
                try:
                    tree = javalang.parse.parse(code)
                except:
                    continue

                try:
                    filters = [javalang.tree.MethodDeclaration, javalang.tree.MethodInvocation, javalang.tree.ClassDeclaration, javalang.tree.ConstructorDeclaration]
                    for filter in filters:
                        for path, node in tree.filter(filter):
                            # Find the line number of the method declaration
                            start_line = node.position[0]
                            # Replace the method name in the line
                            codelines[start_line-1] = codelines[start_line-1].replace(old_method_name, new_method_name)
                except:
                    print(f"Error filtering tree with {filter} for {root}/{file}")
                with open(os.path.join(root, file), 'w') as f:
                    f.write('\n'.join(codelines))