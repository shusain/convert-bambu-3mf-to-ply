import xml.etree.ElementTree as ET
import sys

# Color map for paint_color attributes
COLOR_MAP = {
    "0C": (255, 0, 0),
    "8": (0, 255, 0),
    # Add more as needed
}

def parse_3mf_mesh(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    ns = {'ns': "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}

    vertices_by_index = []
    triangles_raw = []

    mesh = root.find('.//ns:mesh', ns)
    verts_tag = mesh.find('ns:vertices', ns)
    tris_tag = mesh.find('ns:triangles', ns)

    if verts_tag is None or tris_tag is None:
        print("No mesh data found.")
        return [], []

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
        color = COLOR_MAP.get(color_key, (200, 200, 200))  # Default gray
        triangles_raw.append((v1, v2, v3, color))

    return vertices_by_index, triangles_raw

def explode_faces_to_colored_vertices(vertices, triangles):
    new_vertices = []
    new_faces = []

    for tri in triangles:
        v1, v2, v3, color = tri

        # Duplicate each vertex with its color
        for idx in (v1, v2, v3):
            x, y, z = vertices[idx]
            r, g, b = color
            new_vertices.append((x, y, z, r, g, b))

        # Add new face using latest 3 added verts
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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert_3mf_to_ply.py input.xml output.ply")
        sys.exit(1)

    xml_path = sys.argv[1]
    output_path = sys.argv[2]

    verts, tris = parse_3mf_mesh(xml_path)
    if verts and tris:
        colored_verts, faces = explode_faces_to_colored_vertices(verts, tris)
        write_colored_ply(colored_verts, faces, output_path)
        print(f"PLY written to {output_path} with {len(colored_verts)} vertices and {len(faces)} faces")
    else:
        print("No mesh data extracted.")
