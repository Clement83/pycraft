from .base import BaseAnimal

class Snake(BaseAnimal):
    def __init__(self, x, y, z, animal_type):
        super().__init__(x, y, z, animal_type, width=0.5, height=0.5)
