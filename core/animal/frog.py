from .base import BaseAnimal
import random

class Frog(BaseAnimal):
    def __init__(self, x, y, z, animal_type):
        super().__init__(x, y, z, animal_type, width=0.3, height=0.3)
        self.base_speed = 1.0 # Vitesse horizontale pendant le saut
        self.jump_strength = 3.0 # Force du saut
        self.jump_cooldown = 0.0 # Temps avant le prochain saut
        self.max_jump_cooldown = 2.0 # Temps max entre les sauts
        self.on_ground = True # Indique si la grenouille est au sol

    def _choose_new_random_direction(self, world_info):
        # Les grenouilles sautent aléatoirement si elles sont au sol
        if self.on_ground and self.jump_cooldown <= 0:
            self.velocity[1] = self.jump_strength # Impulsion vers le haut
            # Direction horizontale aléatoire pour le saut
            self.velocity[0] = random.uniform(-self.base_speed, self.base_speed)
            self.velocity[2] = random.uniform(-self.base_speed, self.base_speed)
            self.jump_cooldown = self.max_jump_cooldown # Réinitialiser le cooldown
            self.on_ground = False # La grenouille n'est plus au sol
        else:
            # Si pas de saut, pas de mouvement horizontal (sauf si déjà en l'air)
            if self.on_ground:
                self.velocity[0] = 0
                self.velocity[2] = 0
        self.direction_timer = random.uniform(0.5, 1.5) # Temps court avant de re-vérifier le saut

    def update(self, dt, player_pos, world_info):
        # Sauvegarder la vélocité Y avant la mise à jour de base
        prev_vy = self.velocity[1]

        # Appeler la logique de base
        super().update(dt, player_pos, world_info)

        # Détecter l'atterrissage
        if prev_vy < 0 and self.velocity[1] == 0 and not self.on_ground:
            self.on_ground = True
            self.velocity[0] = 0 # Arrêter le mouvement horizontal à l'atterrissage
            self.velocity[2] = 0

        # Diminuer le cooldown de saut
        self.jump_cooldown -= dt
