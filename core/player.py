import math
from pyglet.window import key

# Constants
GRAVITY = -20.0
JUMP_HEIGHT = 8.0
PLAYER_HEIGHT = 1.8
PLAYER_WIDTH = 0.6
EYE_HEIGHT = 1

class Player:
    def __init__(self, position=(0, 2, 0)):
        self.position = list(position)
        self.pitch = 0.0
        self.yaw = 0.0
        self.speed = 10.0
        self.ground_speed = 4.0

        self.ghost_mode = True
        self.velocity_y = 0.0
        self.on_ground = False
        self.debug_info = ""

    def toggle_ghost_mode(self):
        self.ghost_mode = not self.ghost_mode
        self.velocity_y = 0

    def update(self, dt, keys, world):
        yaw_rad = math.radians(self.yaw)
        forward_x = math.sin(yaw_rad)
        forward_z = -math.cos(yaw_rad)
        right_x = math.sin(yaw_rad + math.pi / 2)
        right_z = -math.cos(yaw_rad + math.pi / 2)

        current_speed = self.speed if self.ghost_mode else self.ground_speed
        movement_speed = current_speed * dt
        dx, dz = 0, 0

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
        else:
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
            self.on_ground = False
        else:
            if dy < 0:
                self.on_ground = True
                self.velocity_y = 0
                y = math.floor(ny) + 1
            elif dy > 0:
                self.velocity_y = 0

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