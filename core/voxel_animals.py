# voxel_animals.py
# Fichier prêt à importer dans ton projet Pyglet

import pyglet
from pyglet.gl import *
from pyglet import graphics
from pyglet.math import Mat4, Vec3 # Import Mat4 and Vec3

# ------------------------------
# Modèles voxel
# Chaque voxel = (x, y, z, (r,g,b))
# ------------------------------

# --- Snow biome ---
reindeer_voxel = [
    (1,2,1,(139,69,19)), (1,2,2,(139,69,19)), (2,2,1,(139,69,19)), (2,2,2,(139,69,19)),
    (0,3,1,(222,184,135)), (3,3,2,(222,184,135)),
    (1,1,1,(160,82,45)), (1,1,2,(160,82,45)), (2,1,1,(160,82,45)), (2,1,2,(160,82,45)),
    (1,0,1,(160,82,45)), (1,0,2,(160,82,45)), (2,0,1,(160,82,45)), (2,0,2,(160,82,45)),
    (0,0,1,(101,67,33)), (3,0,2,(101,67,33))
]

penguin_voxel = [
    (1,0,1,(0,0,0)), (1,0,2,(0,0,0)), (2,0,1,(0,0,0)), (2,0,2,(0,0,0)),
    (1,1,1,(255,255,255)), (1,1,2,(255,255,255)), (2,1,1,(255,255,255)), (2,1,2,(255,255,255)),
    (1,2,1,(0,0,0)), (2,2,1,(0,0,0)),
    (1,2,2,(255,165,0))
]

# --- Taiga biome ---
wolf_voxel = [
    (1,2,1,(128,128,128)), (1,2,2,(128,128,128)), (2,2,1,(128,128,128)), (2,2,2,(128,128,128)),
    (0,3,1,(105,105,105)), (3,3,2,(105,105,105)),
    (1,1,1,(169,169,169)), (1,1,2,(169,169,169)), (2,1,1,(169,169,169)), (2,1,2,(169,169,169)),
    (1,0,1,(169,169,169)), (1,0,2,(169,169,169)), (2,0,1,(169,169,169)), (2,0,2,(169,169,169))
]

owl_voxel = [
    (1,0,1,(139,69,19)), (2,0,1,(139,69,19)),
    (1,1,1,(222,184,135)), (2,1,1,(222,184,135)),
    (1,2,1,(255,255,255)), (2,2,1,(255,255,255)), (1,2,2,(0,0,0)), (2,2,2,(0,0,0))
]

# --- Forest biome ---
deer_voxel = [
    (1,2,1,(160,82,45)), (1,2,2,(160,82,45)), (2,2,1,(160,82,45)), (2,2,2,(160,82,45)),
    (0,3,1,(222,184,135)), (3,3,2,(222,184,135)),
    (1,1,1,(139,69,19)), (1,1,2,(139,69,19)), (2,1,1,(139,69,19)), (2,1,2,(139,69,19))
]

fox_voxel = [
    (1,0,1,(255,69,0)), (1,0,2,(255,69,0)), (2,0,1,(255,69,0)), (2,0,2,(255,69,0)),
    (1,1,1,(255,140,0)), (1,1,2,(255,140,0)), (2,1,1,(255,140,0)), (2,1,2,(255,140,0)),
    (1,2,1,(255,69,0)), (2,2,1,(255,69,0)),
    (3,1,1,(255,69,0)), (3,1,2,(255,69,0))
]

# --- Plains biome ---
cow_voxel = [
    (1,0,1,(139,69,19)), (1,0,2,(139,69,19)), (2,0,1,(139,69,19)), (2,0,2,(139,69,19)),
    (1,1,1,(255,255,255)), (1,1,2,(255,255,255)), (2,1,1,(255,255,255)), (2,1,2,(255,255,255)),
    (1,2,1,(139,69,19)), (2,2,1,(139,69,19)),
    (0,0,1,(0,0,0)), (3,0,2,(0,0,0))
]

sheep_voxel = [
    (1,0,1,(255,255,255)), (1,0,2,(255,255,255)), (2,0,1,(255,255,255)), (2,0,2,(255,255,255)),
    (1,1,1,(128,128,128)), (2,1,1,(128,128,128))
]

# --- Savanna biome ---
lion_voxel = [
    (1,2,1,(210,180,140)), (1,2,2,(210,180,140)), (2,2,1,(210,180,140)), (2,2,2,(210,180,140)),
    (0,3,1,(139,69,19)), (3,3,2,(139,69,19)),
    (1,1,1,(222,184,135)), (1,1,2,(222,184,135)), (2,1,1,(222,184,135)), (2,1,2,(222,184,135))
]

zebra_voxel = [
    (1,0,1,(255,255,255)), (1,0,2,(255,255,255)), (2,0,1,(255,255,255)), (2,0,2,(255,255,255)),
    (1,1,1,(0,0,0)), (2,1,2,(0,0,0)),
    (1,2,1,(255,255,255)), (2,2,1,(255,255,255))
]

# --- Desert biome ---
camel_voxel = [
    (1,2,1,(210,180,140)), (2,2,1,(210,180,140)),
    (1,1,2,(160,82,45)), (2,1,2,(160,82,45)),
    (1,0,1,(222,184,135)), (1,0,2,(222,184,135)), (2,0,1,(222,184,135)), (2,0,2,(222,184,135))
]

fennec_voxel = [
    (1,0,1,(255,228,181)), (1,0,2,(255,228,181)), (2,0,1,(255,228,181)), (2,0,2,(255,228,181)),
    (1,1,1,(255,228,181)), (2,1,1,(255,228,181)),
    (0,2,1,(255,160,122)), (3,2,1,(255,160,122))
]

# --- Jungle biome ---
monkey_voxel = [
    (1,0,1,(139,69,19)), (1,0,2,(139,69,19)), (2,0,1,(139,69,19)), (2,0,2,(139,69,19)),
    (1,1,1,(160,82,45)), (2,1,1,(160,82,45)),
    (0,0,1,(160,82,45)), (3,0,2,(160,82,45))
]

parrot_voxel = [
    (1,0,1,(0,255,0)), (1,0,2,(0,255,0)), (2,0,1,(0,255,0)), (2,0,2,(0,255,0)),
    (1,1,1,(255,0,0)), (2,1,1,(255,0,0)),
    (1,2,1,(255,255,0))
]

# ------------------------------
# Dictionnaire par biome
# ------------------------------
biome_animals = {
    "snow": [reindeer_voxel, penguin_voxel],
    "taiga": [wolf_voxel, owl_voxel],
    "forest": [deer_voxel, fox_voxel],
    "plains": [cow_voxel, sheep_voxel],
    "savanna": [lion_voxel, zebra_voxel],
    "desert": [camel_voxel, fennec_voxel],
    "jungle": [monkey_voxel, parrot_voxel]
}

# ------------------------------
# Fonction pour créer un vertex list de voxel et l'ajouter à un batch
# ------------------------------
def draw_voxel_model(model_voxels, program, batch, size=1):
    all_vertices = []
    all_colors = []
    all_indices = []
    
    vertex_offset = 0 # Keep track of the current vertex offset for indexing

    # Define the 8 vertices of a unit cube relative to its origin (0,0,0)
    # and the indices for its 6 faces (12 triangles)
    # This is a standard cube definition
    # Each face has 4 vertices, so 6 faces * 4 vertices = 24 vertices per cube
    cube_vertices_base = [
        # Front face (z=1)
        0.0, 0.0, 1.0,  1.0, 0.0, 1.0,  1.0, 1.0, 1.0,  0.0, 1.0, 1.0,
        # Back face (z=0)
        0.0, 0.0, 0.0,  1.0, 0.0, 0.0,  1.0, 1.0, 0.0,  0.0, 1.0, 0.0,
        # Top face (y=1)
        0.0, 1.0, 0.0,  1.0, 1.0, 0.0,  1.0, 1.0, 1.0,  0.0, 1.0, 1.0,
        # Bottom face (y=0)
        0.0, 0.0, 0.0,  1.0, 0.0, 0.0,  1.0, 0.0, 1.0,  0.0, 0.0, 1.0,
        # Right face (x=1)
        1.0, 0.0, 0.0,  1.0, 0.0, 1.0,  1.0, 1.0, 1.0,  1.0, 1.0, 0.0,
        # Left face (x=0)
        0.0, 0.0, 0.0,  0.0, 0.0, 1.0,  0.0, 1.0, 1.0,  0.0, 1.0, 0.0
    ]

    # Indices for the cube (each face is two triangles)
    # These indices refer to the 24 vertices defined above for a single cube
    cube_indices_base = [
        0, 1, 2, 0, 2, 3,    # Front
        4, 5, 6, 4, 6, 7,    # Back
        8, 9, 10, 8, 10, 11, # Top
        12, 13, 14, 12, 14, 15, # Bottom
        16, 17, 18, 16, 18, 19, # Right
        20, 21, 22, 20, 22, 23  # Left
    ]

    for x, y, z, color in model_voxels:
        r, g, b = [c / 255 for c in color]
        
        # For each voxel, add its transformed vertices and colors
        for i in range(0, len(cube_vertices_base), 3):
            vx = cube_vertices_base[i]
            vy = cube_vertices_base[i+1]
            vz = cube_vertices_base[i+2]
            
            # Apply size and translation
            all_vertices.extend([(vx * size) + (x * size), (vy * size) + (y * size), (vz * size) + (z * size)])
            all_colors.extend([r, g, b])
        
        # Add indices for the current voxel, offsetting them by the current vertex_offset
        all_indices.extend([idx + vertex_offset for idx in cube_indices_base])
        vertex_offset += len(cube_vertices_base) // 3 # Increment offset by the number of vertices in one cube (24)

    # Add the vertex data to the batch using program.vertex_list_indexed
    # This function now returns the created vertex list
    return program.vertex_list_indexed(len(all_vertices) // 3, pyglet.gl.GL_TRIANGLES, all_indices, batch, None,
                                position=('f', all_vertices),
                                colors=('f', all_colors))