from .base import BaseAnimal

class Giraf(BaseAnimal):
    def __init__(self, x, y, z, animal_type):
        super().__init__(x, y, z, animal_type, width=1.5, height=4.0)
