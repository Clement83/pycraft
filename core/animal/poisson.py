from .base import BaseAnimal
import random

class Poisson(BaseAnimal):
    def __init__(self, x, y, z, animal_type):
        super().__init__(x, y, z, animal_type)
        self.base_speed = 1.0 # Vitesse de base plus élevée
        self.gravity_multiplier = 0.01 # Flotte beaucoup

    def _choose_new_random_direction(self, world_info):
        """Les poissons peuvent se déplacer verticalement dans l'eau."""
        vx = random.uniform(-self.base_speed, self.base_speed)
        vy = random.uniform(-self.base_speed * 0.5, self.base_speed * 0.5) # Mouvement vertical
        vz = random.uniform(-self.base_speed, self.base_speed)
        self.velocity = [vx, vy, vz]
        self.direction_timer = random.uniform(1.5, 4) # Changent de direction plus souvent

    def update(self, dt, player_pos, world_info):
        # Appeler la logique de base qui gère la vélocité, la fuite, la gravité, etc.
        super().update(dt, player_pos, world_info)

        # Contrainte supplémentaire : rester dans l'eau
        if self.y > -0.2:
            self.y = -0.2
            if self.velocity[1] > 0:
                self.velocity[1] = 0 # Arrêter le mouvement vers le haut