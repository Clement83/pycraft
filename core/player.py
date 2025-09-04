import math
from pyglet.window import key

class Player:
    def __init__(self, position=(0, 2, 0), rotation=(0, 0)):
        self.position = list(position)
        self.rotation = list(rotation)
        self.velocity = [0, 0, 0]  # vx, vy, vz
        self.on_ground = False
        self.gravity = -20.0
        self.jump_speed = 8.0
        self.fly_mode = True

    def update(self, dt, keys, world):
        speed = dt * 5
        if self.fly_mode:
            speed *= 3 
        yaw = math.radians(-self.rotation[1])
        forward = (math.sin(yaw), 0, math.cos(yaw))
        right = (math.cos(yaw), 0, -math.sin(yaw))

        dx = dz = 0
        if keys[key.UP] or keys[key.W]:
            dx += forward[0]*speed
            dz += forward[2]*speed
        if keys[key.DOWN] or keys[key.S]:
            dx -= forward[0]*speed
            dz -= forward[2]*speed
        if keys[key.LEFT] or keys[key.A]:
            dx += right[0]*speed
            dz += right[2]*speed
        if keys[key.RIGHT] or keys[key.D]:
            dx -= right[0]*speed
            dz -= right[2]*speed

        if self.fly_mode:
            dy = 0
            if keys[key.SPACE]:
                dy += speed
            if keys[key.LSHIFT]:
                dy -= speed
            self.position[0] += dx
            self.position[1] += dy
            self.position[2] += dz
            return

        # Gravité
        self.velocity[1] += self.gravity * dt

        # Saut
        if keys[key.SPACE] and self.on_ground:
            self.velocity[1] = self.jump_speed
            self.on_ground = False

        # Vérifier si dans l'eau
        in_water = self.position[1] < 0
        if in_water:
            self.velocity[1] += 10.0 * dt    # poussée
            self.velocity[1] *= 0.5          # résistance verticale
            speed_multiplier = 0.5           # résistance horizontale
            if keys[key.SPACE]:
                self.velocity[1] += self.jump_speed
        else:
            speed_multiplier = 1.0

        # Déplacement horizontal et vertical
        self.move_with_collision(dx*speed_multiplier, 0, dz*speed_multiplier, world)
        self.move_with_collision(0, self.velocity[1]*dt, 0, world)

    def move_with_collision(self, dx, dy, dz, world):
        half_width = 0.45
        height = 0.95

        # Déplacement sur X
        new_x = self.position[0] + dx
        if not self.check_collision(new_x, self.position[1], self.position[2], half_width, height, world):
            self.position[0] = new_x

        # Déplacement sur Z
        new_z = self.position[2] + dz
        if not self.check_collision(self.position[0], self.position[1], new_z, half_width, height, world):
            self.position[2] = new_z

        # Déplacement sur Y
        new_y = self.position[1] + dy
        self.on_ground = False
        if not self.check_collision(self.position[0], new_y, self.position[2], half_width, height, world):
            self.position[1] = new_y
        else:
            if dy < 0:
                self.on_ground = True
            self.velocity[1] = 0

    def check_collision(self, x, y, z, half_width, height, world):
        for xi in range(math.floor(x - half_width), math.ceil(x + half_width)):
            for yi in range(math.floor(y), math.ceil(y + height)):
                for zi in range(math.floor(z - half_width), math.ceil(z + half_width)):
                    if (xi, yi, zi) in world.blocks:
                        return True
        return False

    def toggle_fly(self):
        self.fly_mode = not self.fly_mode
