from .base import BaseAnimal

class Cerf(BaseAnimal):
    def __init__(self, x, y, z, animal_type):
        super().__init__(x, y, z, animal_type, width=2, height=2.0)
