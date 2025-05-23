import os


def print_directory_tree(root_dir, indent=""):
    # Игнорируем виртуальное окружение и другие ненужные папки
    ignore_dirs = {'.venv', '__pycache__'}

    for item in sorted(os.listdir(root_dir)):
        item_path = os.path.join(root_dir, item)
        if os.path.isdir(item_path):
            if item not in ignore_dirs:
                print(f"{indent}├───{item}")
                print_directory_tree(item_path, indent + "│   ")
        else:
            print(f"{indent}│   {item}")


if __name__ == "__main__":
    project_root = "."  # Текущая директория
    print(f"Project structure: {project_root}")
    print_directory_tree(project_root)