import noise
import random
import math
import threading

class Vegetation:
    def __init__(self, seed=0):
        self.seed = seed
        self.tree_positions = set()  # pour mémoriser où les arbres sont déjà placés
        # self.lock = threading.Lock()  # verrou pour la concurrence

    def has_tree(self, x, z, biome):
        """Décide si un arbre/cactus pousse ici selon le bruit et le biome"""
        freq = 20  # plus petit = arbres plus rapprochés
        val = noise.pnoise2(x / freq, z / freq, octaves=2, base=self.seed)
        val = (val + 1) / 2

        if biome == "forest":
            return val > 0.5
        elif biome == "taiga":
            return val > 0.55
        elif biome == "jungle":
            return val > 0.40
        elif biome == "plains":
            return val > 0.6
        elif biome == "savanna":
            return val > 0.55
        elif biome == "desert":
            return val > 0.65
        else:
            return False

    def can_place_tree(self, x, z, min_distance=6):
        """Vérifie si un arbre est trop proche"""
        # with self.lock:
        for tx, tz in self.tree_positions:
            if math.hypot(tx - x, tz - z) < min_distance:
                return False
        return True

    def register_tree(self, x, z):
        """Ajoute l'arbre à la liste des positions"""
        # with self.lock:
        self.tree_positions.add((x, z))

    def generate(self, chunk_blocks, x, z, y, biome):
        """Génère la végétation (arbre/cactus) au-dessus du sol"""
        if self.has_tree(x, z, biome) and self.can_place_tree(x, z):
            self.register_tree(x, z)

            if biome == "forest":
                self._tree_oak(chunk_blocks, x, z, y)
            elif biome == "taiga":
                self._tree_pine(chunk_blocks, x, z, y)
            elif biome == "jungle":
                self._tree_jungle(chunk_blocks, x, z, y)
            elif biome == "plains":
                self._tree_small(chunk_blocks, x, z, y)
            elif biome == "desert":
                self._cactus(chunk_blocks, x, z, y)
            elif biome == "savanna":
                self._tree_acacia(chunk_blocks, x, z, y)
    # -----------------------------
    # Types d’arbres
    # -----------------------------

    def _tree_oak(self, blocks, x, z, y):
        height = random.randint(2, 4)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        # petite boule de feuilles
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                for dy in range(0, 2):
                    if abs(dx) + abs(dz) + dy < 3:
                        blocks[(x+dx, y+height-1+dy, z+dz)] = "leaves"

    def _tree_pine(self, blocks, x, z, y):
        height = random.randint(3, 5)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        radius = 2
        for dy in range(height//2, height+1):
            for dx in range(-radius, radius+1):
                for dz in range(-radius, radius+1):
                    if dx**2 + dz**2 <= radius**2:
                        blocks[(x+dx, y+dy, z+dz)] = "leaves"
            radius = max(1, radius-1)

    def _tree_jungle(self, blocks, x, z, y):
        height = random.randint(4, 6)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        # feuillage un peu plus large
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(0, 2):
                    if dx**2 + dz**2 + dy**2 < 6:
                        blocks[(x+dx, y+height-1+dy, z+dz)] = "leaves"

    def _tree_small(self, blocks, x, z, y):
        height = random.randint(2, 3)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        # petit toupet
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                blocks[(x+dx, y+height, z+dz)] = "leaves"

    def _cactus(self, blocks, x, z, y):
        height = random.randint(2, 3)
        for i in range(height):
            blocks[(x, y+i, z)] = "cactus"

    def _tree_acacia(self, blocks, x, z, y):
        height = random.randint(3, 4)
        for i in range(height):
            blocks[(x, y+i, z)] = "log"
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if abs(dx) + abs(dz) < 3:
                    blocks[(x+dx, y+height, z+dz)] = "leaves"
