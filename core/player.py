import math
from pyglet.window import key

# Constants
GRAVITY = -20.0
JUMP_HEIGHT = 8.0
PLAYER_HEIGHT = 1.8
PLAYER_WIDTH = 0.6
EYE_HEIGHT = 1.6

# Swimming constants
SWIM_GRAVITY = -10.0 # Coule un peu plus vite pour être plus visible
SWIM_SPEED_MULTIPLIER = 1.5 # faster movement in water
SWIM_VERTICAL_SPEED = 5.0 # Speed for ascending/descending in water

class Player:
    def __init__(self, position=(0, 2, 0)):
        self.position = list(position)
        self.pitch = 0.0
        self.yaw = 0.0
        self.speed = 10.0
        self.ground_speed = 4.0

        self.ghost_mode = True # Default to ghost mode
        self.is_swimming = False # New flag for swimming
        self.velocity_y = 0.0
        self.on_ground = False
        self.debug_info = ""

    def toggle_ghost_mode(self):
        self.ghost_mode = not self.ghost_mode
        self.velocity_y = 0 # Reset vertical velocity when changing modes
        self.is_swimming = False # Exit swimming if toggling ghost mode

    def update(self, dt, keys, world):
        # Determine if player is in water
        # Player's feet are at y, water level is at 0. So if y <= -1, player is in water.
        # Also check if the block at player's feet is water
        feet_block_pos = (round(self.position[0]), math.floor(self.position[1]), round(self.position[2]))
        is_in_water_block = world.blocks.get(feet_block_pos) == 'water'

        was_swimming = self.is_swimming # Store previous state

        # Determine if player is in water
        # Player's feet are at y, water level is at 0. So if y <= -1, player is in water.
        # Also check if the block at player's feet is water
        feet_block_pos = (round(self.position[0]), math.floor(self.position[1]), round(self.position[2]))
        is_in_water_block = world.blocks.get(feet_block_pos) == 'water'

        # Swimming condition: player's eyes are at or below water level (y=0)
        if self.position[1] + EYE_HEIGHT < 0:
            if (self.is_swimming): 
                self.velocity_y = 0
            self.is_swimming = True
        else:
            self.is_swimming = False

        yaw_rad = math.radians(self.yaw)
        forward_x = math.sin(yaw_rad)
        forward_z = -math.cos(yaw_rad)
        right_x = math.sin(yaw_rad + math.pi / 2)
        right_z = -math.cos(yaw_rad + math.pi / 2)

        current_speed = self.speed if self.ghost_mode else self.ground_speed
        movement_speed = current_speed * dt
        dx, dz, dy = 0, 0, 0

        if keys[key.W] or keys[key.UP]:
            dx += forward_x * movement_speed
            dz += forward_z * movement_speed
        if keys[key.S] or keys[key.DOWN]:
            dx -= forward_x * movement_speed
            dz -= forward_z * movement_speed
        if keys[key.A] or keys[key.LEFT]:
            dx -= right_x * movement_speed
            dz -= right_z * movement_speed
        if keys[key.D] or keys[key.RIGHT]:
            dx += right_x * movement_speed
            dz += right_z * movement_speed

        if self.ghost_mode:
            self.on_ground = False
            pitch_rad = math.radians(self.pitch)
            forward_y = -math.sin(pitch_rad)

            if keys[key.W] or keys[key.UP]:
                self.position[1] += forward_y * movement_speed
            if keys[key.S] or keys[key.DOWN]:
                self.position[1] -= forward_y * movement_speed
            if keys[key.SPACE]:
                self.position[1] += movement_speed
            if keys[key.LSHIFT]:
                self.position[1] -= movement_speed
            
            self.position[0] += dx
            self.position[2] += dz
        elif self.is_swimming:
            # Swimming mode: déplacement comme en ghost mais avec collisions et gravité de natation
            
            # Appliquer la gravité de natation
            self.velocity_y += SWIM_GRAVITY * dt
            
            # Mouvement vertical basé sur le pitch (comme en ghost mode)
            pitch_rad = math.radians(self.pitch)
            forward_y = -math.sin(pitch_rad)

            if keys[key.W] or keys[key.UP]:
                dy += forward_y * movement_speed * SWIM_SPEED_MULTIPLIER
            if keys[key.S] or keys[key.DOWN]:
                dy -= forward_y * movement_speed * SWIM_SPEED_MULTIPLIER
            
            # Mouvement vertical direct avec espace et shift
            if keys[key.SPACE]:
                dy += movement_speed * SWIM_SPEED_MULTIPLIER
            if keys[key.LSHIFT]:
                dy -= movement_speed * SWIM_SPEED_MULTIPLIER
            
            # Ajouter la vélocité verticale due à la gravité
            dy += self.velocity_y * dt
            
            # Appliquer le ralentissement de la natation aux mouvements horizontaux
            dx *= SWIM_SPEED_MULTIPLIER
            dz *= SWIM_SPEED_MULTIPLIER

            # Utiliser la gestion des collisions
            self._collide_and_move(dx, dy, dz, world)

        else: # Ground mode
            # Check for transition from swimming to ground mode
            if was_swimming and not self.is_swimming:
                # If player was moving upwards (e.g., pressing space)
                if keys[key.SPACE]: # Or check if dy was positive before collision
                    self.velocity_y = JUMP_HEIGHT # Give them a jump boost
                    self.on_ground = False # They are now airborne

            if keys[key.SPACE] and self.on_ground:
                self.velocity_y = JUMP_HEIGHT
            
            self.velocity_y += GRAVITY * dt
            dy = self.velocity_y * dt

            self._collide_and_move(dx, dy, dz, world)

    def _collide_and_move(self, dx, dy, dz, world):
        x, y, z = self.position

        # X-axis
        nx = x + dx
        if not self._is_colliding(nx, y, z, world):
            x = nx

        # Z-axis
        nz = z + dz
        if not self._is_colliding(x, y, nz, world):
            z = nz

        # Y-axis
        ny = y + dy
        if not self._is_colliding(x, ny, z, world):
            y = ny
            # En mode natation, on ne se pose pas au sol
            if not self.is_swimming:
                self.on_ground = False
        else:
            # Gestion des collisions différente selon le mode
            if not self.is_swimming:
                # Mode ground : comportement normal
                if dy < 0:
                    self.on_ground = True
                    self.velocity_y = 0
                    y = math.floor(ny) + 1
                elif dy > 0:
                    self.velocity_y = 0
            else:
                # Mode natation : arrêter le mouvement mais garder un peu de velocity pour l'effet de coulée
                if dy < 0:
                    # Si on heurte le sol en coulant, on s'arrête mais on garde une petite velocity négative
                    self.velocity_y = max(self.velocity_y, -1.0)
                    y = math.floor(ny) + 1
                elif dy > 0:
                    # Si on heurte le plafond, on s'arrête
                    self.velocity_y = min(self.velocity_y, 0.0)

        self.position = [x, y, z]

    def _is_colliding(self, x, y, z, world):
        w = PLAYER_WIDTH / 2
        # Feet
        for dx in [-w, w]:
            for dz in [-w, w]:
                feet_pos = (round(x + dx), math.floor(y), round(z + dz))
                if world.is_solid(feet_pos):
                    return True
        # Head
        for dx in [-w, w]:
            for dz in [-w, w]:
                head_pos = (round(x + dx), math.floor(y + PLAYER_HEIGHT), round(z + dz))
                if world.is_solid(head_pos):
                    return True
        return False

    def rotate(self, delta_pitch, delta_yaw):
        self.pitch += delta_pitch
        self.yaw += delta_yaw
        self.pitch = max(-90, min(90, self.pitch))