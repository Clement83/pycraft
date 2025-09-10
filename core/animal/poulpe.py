from .base import BaseAnimal
import random

class Poulpe(BaseAnimal):
    def __init__(self, x, y, z, animal_type):
        super().__init__(x, y, z, animal_type)
        self.base_speed = 0.6 # Plus lent que le poisson
        self.gravity_multiplier = 0.3 # Flotte un peu moins que le poisson

    def _choose_new_random_direction(self, world_info):
        """Le poulpe se déplace lentement, avec des sauts occasionnels."""
        # 1 chance sur 4 de faire un saut vers le haut
        if random.randint(0, 4) == 0:
            self.velocity[1] = self.base_speed * 5 # Impulsion vers le haut augmentée

        vx = random.uniform(-self.base_speed, self.base_speed)
        vy = self.velocity[1] # Conserver l'impulsion du saut ou la gravité
        vz = random.uniform(-self.base_speed, self.base_speed)
        self.velocity = [vx, vy, vz]
        self.direction_timer = random.uniform(3, 6) # Changements de direction lents

    def update(self, dt, player_pos, world_info):
        # Appeler la logique de base
        super().update(dt, player_pos, world_info)

        # Contrainte : rester dans l'eau
        if self.y > -0.5:
            self.y = -0.5
            if self.velocity[1] > 0:
                self.velocity[1] = 0