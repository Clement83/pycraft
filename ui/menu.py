import pyglet
from pyglet.text import Label
from pyglet.shapes import Rectangle

class TextInput:
    def __init__(self, x, y, width, height, text='', max_length=10):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.max_length = max_length
        self.active = False

        self.rectangle = Rectangle(x, y, width, height, color=(255, 255, 255))
        self.label = Label(text, x=x + 5, y=y + height // 2, anchor_y='center', color=(0, 0, 0, 255))
        self.caret = Rectangle(0, 0, 2, height - 4, color=(0, 0, 0))

    def draw(self):
        self.rectangle.draw()
        self.label.draw()
        if self.active:
            self.caret.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        self.active = self.x < x < self.x + self.width and self.y < y < self.y + self.height

    def on_text(self, text):
        if self.active and len(self.text) < self.max_length:
            self.text += text
            self.label.text = self.text
            self.update_caret()

    def on_key_press(self, symbol, modifiers):
        if self.active:
            if symbol == pyglet.window.key.BACKSPACE:
                self.text = self.text[:-1]
                self.label.text = self.text
                self.update_caret()

    def update_caret(self):
        self.caret.x = self.x + self.label.content_width + 6
        self.caret.y = self.y + 2

class Button:
    def __init__(self, x, y, width, height, text, on_click):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.on_click = on_click

        self.rectangle = Rectangle(x, y, width, height, color=(100, 100, 100))
        self.label = Label(text, x=x + width // 2, y=y + height // 2, anchor_x='center', anchor_y='center', font_size=18)

    def draw(self):
        self.rectangle.draw()
        self.label.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.x < x < self.x + self.width and self.y < y < self.y + self.height:
            if self.on_click:
                self.on_click()

class Menu:
    def __init__(self, window, start_game_callback):
        self.window = window
        self.start_game_callback = start_game_callback

        self.title = Label('pyCraft Infinite', font_size=36, x=window.width // 2, y=window.height - 100, anchor_x='center')
        
        self.seed_label = Label('Seed:', font_size=18, x=window.width // 2 - 100, y=window.height // 2, anchor_x='right')
        self.seed_input = TextInput(window.width // 2 - 90, window.height // 2 - 15, 180, 30)

        self.start_button = Button(window.width // 2 - 50, window.height // 2 - 80, 100, 40, 'Start', self.start_game)

    def start_game(self):
        seed = self.seed_input.text
        if self.start_game_callback:
            self.start_game_callback(seed)

    def draw(self):
        self.title.draw()
        self.seed_label.draw()
        self.seed_input.draw()
        self.start_button.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        self.seed_input.on_mouse_press(x, y, button, modifiers)
        self.start_button.on_mouse_press(x, y, button, modifiers)

    def on_text(self, text):
        self.seed_input.on_text(text)

    def on_key_press(self, symbol, modifiers):
        self.seed_input.on_key_press(symbol, modifiers)

    def on_resize(self, width, height):
        self.title.x = width // 2
        self.title.y = height - 100
        self.seed_label.x = width // 2 - 100
        self.seed_label.y = height // 2
        self.seed_input.x = width // 2 - 90
        self.seed_input.y = height // 2 - 15
        self.seed_input.rectangle.x = width // 2 - 90
        self.seed_input.rectangle.y = height // 2 - 15
        self.seed_input.label.x = width // 2 - 85
        self.seed_input.label.y = height // 2
        self.start_button.x = width // 2 - 50
        self.start_button.y = height // 2 - 80
        self.start_button.rectangle.x = width // 2 - 50
        self.start_button.rectangle.y = height // 2 - 80
        self.start_button.label.x = width // 2
        self.start_button.label.y = height // 2 - 60

