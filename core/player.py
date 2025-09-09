import math
from pyglet.window import key

class Player:
    def __init__(self, position=(0, 2, 0)):
        self.position = [position[0], position[1], position[2]]
        self.pitch = 0.0  # Rotation verticale (haut/bas)
        self.yaw = 0.0    # Rotation horizontale (gauche/droite)
        self.speed = 10.0

    def update(self, dt, keys):
        # Calculer les vecteurs de direction basés sur les angles
        pitch_rad = math.radians(self.pitch)
        yaw_rad = math.radians(self.yaw)
        
        # Direction avant (forward)
        forward_x = math.sin(yaw_rad) * math.cos(pitch_rad)
        forward_y = -math.sin(pitch_rad)
        forward_z = -math.cos(yaw_rad) * math.cos(pitch_rad)
        
        # Direction droite (right) - perpendiculaire au forward
        right_x = math.sin(yaw_rad + math.pi/2)
        right_z = -math.cos(yaw_rad + math.pi/2)
        
        # Mouvement
        movement_speed = self.speed * dt
        
        # Avant/Arrière
        if keys[key.W] or keys[key.UP]:
            self.position[0] += forward_x * movement_speed
            self.position[1] += forward_y * movement_speed
            self.position[2] += forward_z * movement_speed
        if keys[key.S] or keys[key.DOWN]:
            self.position[0] -= forward_x * movement_speed
            self.position[1] -= forward_y * movement_speed
            self.position[2] -= forward_z * movement_speed
            
        # Gauche/Droite
        if keys[key.A] or keys[key.LEFT]:
            self.position[0] -= right_x * movement_speed
            self.position[2] -= right_z * movement_speed
        if keys[key.D] or keys[key.RIGHT]:
            self.position[0] += right_x * movement_speed
            self.position[2] += right_z * movement_speed
            
        # Haut/Bas (mouvement vertical pur)
        if keys[key.SPACE]:
            self.position[1] += movement_speed
        if keys[key.LSHIFT]:
            self.position[1] -= movement_speed

    def rotate(self, delta_pitch, delta_yaw):
        """Applique une rotation à partir du mouvement de la souris"""
        self.pitch += delta_pitch
        self.yaw += delta_yaw
        
        # Limiter le pitch pour éviter les retournements
        self.pitch = max(-90, min(90, self.pitch))