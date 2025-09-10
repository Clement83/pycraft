import math
import random

class BaseAnimal:
    def __init__(self, x, y, z, animal_type):
        self.x = x
        self.y = y
        self.z = z
        self.type = animal_type
        
        self.width = 0.5
        self.height = 0.5

        # Système de vélocité
        self.base_speed = 0.5 # Vitesse de base pour le calcul de la vélocité
        self.velocity = [0, 0, 0] # [vx, vy, vz]
        self.direction_timer = 0 # Minuteur avant le prochain changement de direction
        self.gravity_multiplier = 1.0 # Multiplicateur pour la gravité (1.0 = normal)

    def update(self, dt, player_pos, world_info):
        """Logique de mise à jour principale basée sur la vélocité."""
        # La fuite modifie directement la vélocité et a la priorité
        is_fleeing = self._flee(player_pos)
        if is_fleeing:
            self.direction_timer = 1.0 # Courte pause avant de reprendre un mouvement normal
        else:
            # Sinon, mouvement normal
            self.direction_timer -= dt
            if self.direction_timer <= 0:
                self._choose_new_random_direction(world_info)

        # Appliquer la gravité à la vélocité Y (toujours appliqué)
        is_solid = world_info.get("is_solid")
        block_below = (round(self.x), math.floor(self.y - 0.1), round(self.z))
        if not is_solid(block_below):
            self.velocity[1] -= 9.8 * dt * 0.5 * self.gravity_multiplier # Gravité
        else:
            self.velocity[1] = max(0, self.velocity[1]) # Arrêter la chute

        # Calculer le déplacement
        dx = self.velocity[0] * dt
        dy = self.velocity[1] * dt
        dz = self.velocity[2] * dt

        # Gérer les collisions et mettre à jour la position
        collided_axes = self._collide_and_move(dx, dy, dz, world_info)
        if collided_axes:
            self._handle_collision(collided_axes)

    def _choose_new_random_direction(self, world_info):
        """Choisit une nouvelle direction aléatoire, en conservant la vélocité Y."""
        vx = random.uniform(-self.base_speed, self.base_speed)
        vz = random.uniform(-self.base_speed, self.base_speed)
        self.velocity[0] = vx
        self.velocity[2] = vz
        # On ne touche pas à self.velocity[1] pour ne pas interrompre la gravité
        self.direction_timer = random.uniform(2, 5) # Prochain changement dans 2 à 5 secondes

    def _handle_collision(self, collided_axes):
        """Gère la réaction à une collision (rebond)."""
        if 'x' in collided_axes:
            self.velocity[0] *= -1
        if 'y' in collided_axes:
            self.velocity[1] = 0
        if 'z' in collided_axes:
            self.velocity[2] *= -1
        self.direction_timer = 0

    def _flee(self, player_pos, flee_distance=7):
        """Si le joueur est proche, modifie la vélocité pour fuir et retourne True."""
        px, _, pz = player_pos
        dist_to_player = math.hypot(self.x - px, self.z - pz)

        if dist_to_player < flee_distance:
            flee_vec_x = self.x - px
            flee_vec_z = self.z - pz
            norm = math.hypot(flee_vec_x, flee_vec_z)
            if norm > 0:
                speed_multiplier = 4.0 # Fuir plus vite
                # On modifie directement la vélocité de l'animal
                self.velocity[0] = (flee_vec_x / norm) * self.base_speed * speed_multiplier
                self.velocity[2] = (flee_vec_z / norm) * self.base_speed * speed_multiplier
                # On ne touche pas à la vélocité Y
                return True # L'animal fuit
        return False # L'animal ne fuit pas

    def _is_colliding(self, x, y, z, world_info):
        is_solid = world_info.get("is_solid")
        if not is_solid:
            return False
        check_pos = (round(x), math.floor(y), round(z))
        return is_solid(check_pos)

    def _collide_and_move(self, dx, dy, dz, world_info):
        collided_axes = set()
        x, y, z = self.x, self.y, self.z
        is_solid = world_info.get("is_solid")

        # --- Mouvement X ---
        nx = x + dx
        if self._is_colliding(nx, y, z, world_info):
            # Obstacle détecté. Est-ce une marche ?
            if not self._is_colliding(nx, y + 1, z, world_info) and not self._is_colliding(x, y + 1, z, world_info):
                # C'est une marche, on monte
                self.y += 1
                # Et on avance
                if not self._is_colliding(nx, self.y, z, world_info):
                    self.x = nx
                else: # Le haut de la marche est bloqué
                    self.y -= 1 # On annule la montée
                    collided_axes.add('x')
            else:
                # C'est un mur
                collided_axes.add('x')
        else:
            # Pas d'obstacle
            self.x = nx

        # --- Mouvement Z ---
        nz = z + dz
        if self._is_colliding(self.x, self.y, nz, world_info):
            if not self._is_colliding(self.x, self.y + 1, nz, world_info):
                self.y += 1
                if not self._is_colliding(self.x, self.y, nz, world_info):
                    self.z = nz
                else:
                    self.y -= 1
                    collided_axes.add('z')
            else:
                collided_axes.add('z')
        else:
            self.z = nz

        # --- Mouvement Y ---
        ny = self.y + dy
        if self._is_colliding(self.x, ny, self.z, world_info):
            collided_axes.add('y')
        else:
            self.y = ny
            
        return collided_axes
