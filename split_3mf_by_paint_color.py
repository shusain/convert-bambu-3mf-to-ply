import zipfile
import os
import tempfile
import shutil
import xml.etree.ElementTree as ET
import sys

def split_3mf_by_paint_color(input_3mf_path):
    temp_dir = tempfile.mkdtemp()
    base_name = os.path.splitext(os.path.basename(input_3mf_path))[0]
    output_colored_path = f"{base_name}_colored.3mf"
    output_uncolored_path = f"{base_name}_uncolored.3mf"

    try:
        with zipfile.ZipFile(input_3mf_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        model_paths = []
        for root_dir, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(".model"):
                    model_paths.append(os.path.join(root_dir, file))

        for model_path in model_paths:
            tree = ET.parse(model_path)
            root = tree.getroot()
            ns = {'ns': "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}

            mesh = root.find('.//ns:mesh', ns)
            if mesh is None:
                continue

            vertices = mesh.find('ns:vertices', ns)
            triangles = mesh.find('ns:triangles', ns)
            if vertices is None or triangles is None:
                continue

            all_vertices = vertices.findall('ns:vertex', ns)
            all_triangles = triangles.findall('ns:triangle', ns)

            used_by_colored = set()
            used_by_uncolored = set()
            colored_tris = []
            uncolored_tris = []

            for tri in all_triangles:
                indices = [int(tri.attrib['v1']), int(tri.attrib['v2']), int(tri.attrib['v3'])]
                if 'paint_color' in tri.attrib:
                    colored_tris.append(tri)
                    used_by_colored.update(indices)
                else:
                    uncolored_tris.append(tri)
                    used_by_uncolored.update(indices)

            def build_filtered_tree(tri_subset, used_vertices):
                new_tree = ET.parse(model_path)
                new_root = new_tree.getroot()
                new_mesh = new_root.find('.//ns:mesh', ns)
                new_verts_tag = new_mesh.find('ns:vertices', ns)
                new_tris_tag = new_mesh.find('ns:triangles', ns)

                vertex_map = {}
                new_vertices = []
                for new_idx, old_idx in enumerate(sorted(used_vertices)):
                    vertex_map[old_idx] = new_idx
                    v = all_vertices[old_idx]
                    new_v = ET.Element('vertex', v.attrib)
                    new_vertices.append(new_v)

                new_triangles = []
                for tri in tri_subset:
                    new_tri = ET.Element('triangle', tri.attrib.copy())
                    new_tri.attrib['v1'] = str(vertex_map[int(tri.attrib['v1'])])
                    new_tri.attrib['v2'] = str(vertex_map[int(tri.attrib['v2'])])
                    new_tri.attrib['v3'] = str(vertex_map[int(tri.attrib['v3'])])
                    new_triangles.append(new_tri)

                new_verts_tag.clear()
                new_verts_tag.extend(new_vertices)

                new_tris_tag.clear()
                new_tris_tag.extend(new_triangles)

                return new_tree

            relative_path = os.path.relpath(model_path, temp_dir)
            colored_model_path = os.path.join(temp_dir + "_colored", relative_path)
            uncolored_model_path = os.path.join(temp_dir + "_uncolored", relative_path)

            os.makedirs(os.path.dirname(colored_model_path), exist_ok=True)
            os.makedirs(os.path.dirname(uncolored_model_path), exist_ok=True)

            build_filtered_tree(colored_tris, used_by_colored).write(colored_model_path)
            build_filtered_tree(uncolored_tris, used_by_uncolored).write(uncolored_model_path)

        def copy_remaining_files(src_dir, dst_dir):
            for foldername, _, filenames in os.walk(src_dir):
                for filename in filenames:
                    src_file = os.path.join(foldername, filename)
                    rel_path = os.path.relpath(src_file, src_dir)
                    dst_file = os.path.join(dst_dir, rel_path)

                    if filename.endswith(".model"):
                        continue  # already handled
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    shutil.copy2(src_file, dst_file)

        colored_dir = temp_dir + "_colored"
        uncolored_dir = temp_dir + "_uncolored"
        copy_remaining_files(temp_dir, colored_dir)
        copy_remaining_files(temp_dir, uncolored_dir)

        def zip_dir(source_dir, zip_path):
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root_dir, _, files in os.walk(source_dir):
                    for file in files:
                        full_path = os.path.join(root_dir, file)
                        rel_path = os.path.relpath(full_path, source_dir)
                        zipf.write(full_path, rel_path)

        zip_dir(colored_dir, output_colored_path)
        zip_dir(uncolored_dir, output_uncolored_path)

        print(f"✅ Created:\n  {output_colored_path}\n  {output_uncolored_path}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(temp_dir + "_colored", ignore_errors=True)
        shutil.rmtree(temp_dir + "_uncolored", ignore_errors=True)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python split_3mf_by_paint_color.py input_file.3mf")
        sys.exit(1)

    input_file = sys.argv[1]
    split_3mf_by_paint_color(input_file)
