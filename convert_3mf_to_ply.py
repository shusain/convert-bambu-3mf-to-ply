import zipfile
import xml.etree.ElementTree as ET
import colorsys
import sys
import os

def generate_color_map(unique_keys):
    """Auto-generate distinct RGB colors for each unique paint_color."""
    color_map = {}
    total = len(unique_keys)
    for i, key in enumerate(sorted(unique_keys)):
        hue = i / max(1, total)
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        color_map[key] = (int(r * 255), int(g * 255), int(b * 255))
    return color_map

def parse_3mf_mesh(archive_path):
    with zipfile.ZipFile(archive_path, 'r') as archive:
        with archive.open('3D/Objects/object_2.model') as model_file:
            tree = ET.parse(model_file)
            root = tree.getroot()

            ns = {'ns': "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}

            vertices_by_index = []
            triangles_raw = []
            color_keys = set()

            mesh = root.find('.//ns:mesh', ns)
            verts_tag = mesh.find('ns:vertices', ns)
            tris_tag = mesh.find('ns:triangles', ns)

            for v in verts_tag.findall('ns:vertex', ns):
                x = float(v.attrib.get('x', 0))
                y = float(v.attrib.get('y', 0))
                z = float(v.attrib.get('z', 0))
                vertices_by_index.append((x, y, z))

            for tri in tris_tag.findall('ns:triangle', ns):
                v1 = int(tri.attrib['v1'])
                v2 = int(tri.attrib['v2'])
                v3 = int(tri.attrib['v3'])
                color_key = tri.attrib.get('paint_color')
                if color_key:
                    color_keys.add(color_key)
                triangles_raw.append((v1, v2, v3, color_key))

            return vertices_by_index, triangles_raw, color_keys

def explode_faces_to_colored_vertices(vertices, triangles, color_map):
    new_vertices = []
    new_faces = []

    for tri in triangles:
        v1, v2, v3, color_key = tri
        color = color_map.get(color_key, (200, 200, 200))  # Default gray

        for idx in (v1, v2, v3):
            x, y, z = vertices[idx]
            r, g, b = color
            new_vertices.append((x, y, z, r, g, b))

        face_start = len(new_vertices) - 3
        new_faces.append((face_start, face_start + 1, face_start + 2))

    return new_vertices, new_faces

def write_colored_ply(vertices, faces, output_path):
    with open(output_path, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(vertices)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write(f"element face {len(faces)}\n")
        f.write("property list uchar int vertex_indices\n")
        f.write("end_header\n")

        for x, y, z, r, g, b in vertices:
            f.write(f"{x} {y} {z} {r} {g} {b}\n")

        for face in faces:
            f.write(f"3 {face[0]} {face[1]} {face[2]}\n")

def main():
    if len(sys.argv) != 3:
        print("Usage: python convert_3mf_to_ply.py input.3mf output.ply")
        sys.exit(1)

    input_3mf = sys.argv[1]
    output_ply = sys.argv[2]

    if not os.path.exists(input_3mf):
        print(f"Error: {input_3mf} does not exist.")
        sys.exit(1)

    verts, tris, color_keys = parse_3mf_mesh(input_3mf)
    color_map = generate_color_map(color_keys)
    colored_verts, faces = explode_faces_to_colored_vertices(verts, tris, color_map)
    write_colored_ply(colored_verts, faces, output_ply)

    print(f"✅ Wrote {output_ply} with {len(colored_verts)} vertices and {len(faces)} faces with {len(color_map)} unique colors.")

if __name__ == "__main__":
    main()
