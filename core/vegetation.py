import random

class Vegetation:
    def __init__(self, seed=0):
        self.seed = seed

    def rand(self, x, z):
        """Retourne un générateur pseudo-aléatoire déterministe basé sur (x, z, seed)."""
        return random.Random((x * 73856093) ^ (z * 19349663) ^ self.seed)

    def hash_noise(self, x, z, seed):
        """Retourne une valeur bruitée déterministe entre 0 et 1."""
        r = random.Random((x * 73856093) ^ (z * 19349663) ^ seed)
        return r.random()

    def has_tree(self, x, z, biome):
        """Décide si un arbre/cactus pousse ici selon le bruit et le biome."""
        val = self.hash_noise(x, z, self.seed)

        if biome == "forest":
            return val > 0.98
        elif biome == "taiga":
            return val > 0.985
        elif biome == "jungle":
            return val > 0.98
        elif biome == "plains":
            return val > 0.99
        elif biome == "savanna":
            return val > 0.98
        elif biome == "desert":
            return val > 0.999
        else:
            return False

    def generate(self, chunk_blocks, x, z, y, biome):
        """Génère la végétation (arbre/cactus) au-dessus du sol."""
        if self.has_tree(x, z, biome):

            if biome == "forest":
                self._tree_oak(biome, chunk_blocks, x, z, y)
            elif biome == "taiga":
                self._tree_pine(biome, chunk_blocks, x, z, y)
            elif biome == "jungle":
                self._tree_jungle(biome, chunk_blocks, x, z, y)
            elif biome == "plains":
                self._tree_small(biome, chunk_blocks, x, z, y)
            elif biome == "desert":
                self._cactus(biome, chunk_blocks, x, z, y)
            elif biome == "savanna":
                self._tree_acacia(biome, chunk_blocks, x, z, y)

    # -----------------------------
    # Types d’arbres
    # -----------------------------

    def _tree_oak(self, biome, blocks, x, z, y):
        r = self.rand(x, z)
        height = r.randint(2, 4)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        # petite boule de feuilles
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                for dy in range(0, 2):
                    if abs(dx) + abs(dz) + dy < 3:
                        blocks[(x+dx, y+height-1+dy, z+dz)] = biome + "/leaves"

    def _tree_pine(self, biome, blocks, x, z, y):
        r = self.rand(x, z)
        height = r.randint(3, 6)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        radius = 2
        for dy in range(height//2, height+1):
            for dx in range(-radius, radius+1):
                for dz in range(-radius, radius+1):
                    if dx**2 + dz**2 <= radius**2:
                        blocks[(x+dx, y+dy, z+dz)] = biome + "/leaves"
            radius = max(1, radius-1)

    def _tree_jungle(self, biome, blocks, x, z, y):
        height = self.rand(x, z).randint(4, 6)
        
        # Tronc
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        
        # Feuillage principal (couche intermédiaire)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(0, 2):
                    if dx**2 + dz**2 + dy**2 < 6:
                        blocks[(x+dx, y+height-2+dy, z+dz)] = biome + "/leaves"

        # Couronne plus large au sommet
        for dx in range(-3, 4):  # élargit à -3..3
            for dz in range(-3, 4):
                if dx**2 + dz**2 < 15:  # cercle un peu plus large
                    blocks[(x+dx, y+height, z+dz)] = biome + "/leaves"

        # Petite pointe feuillue (optionnel, pour donner une forme conique)
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                blocks[(x+dx, y+height+1, z+dz)] = biome + "/leaves"


    def _tree_small(self, biome, blocks, x, z, y):
        r = self.rand(x, z)
        height = r.randint(2, 3)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        # petit toupet
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                blocks[(x+dx, y+height, z+dz)] = biome + "/leaves"

    def _cactus(self, biome, blocks, x, z, y):
        r = self.rand(x, z)
        height = r.randint(2, 3)
        for i in range(height):
            blocks[(x, y+i, z)] = "cactus"

    def _tree_acacia(self, biome, blocks, x, z, y):
        r = self.rand(x, z)
        height = r.randint(3, 4)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if abs(dx) + abs(dz) < 3:
                    blocks[(x+dx, y+height, z+dz)] = biome + "/leaves"
