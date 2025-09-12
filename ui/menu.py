import pyglet
from pyglet.text import Label
from pyglet.shapes import Rectangle
import config

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
    def __init__(self, window, create_game_callback, join_game_callback):
        self.window = window
        self.create_game_callback = create_game_callback
        self.join_game_callback = join_game_callback

        self.title = Label('pyCraft Infinite', font_size=36, x=window.width // 2, y=window.height - 100, anchor_x='center')
        
        self.seed_label = Label('Seed:', font_size=18, x=window.width // 2 - 100, y=window.height // 2, anchor_x='right')
        self.seed_input = TextInput(window.width // 2 - 90, window.height // 2 - 15, 180, 30, text=str(config.WORLD_SEED))

        self.port_label = Label('Port:', font_size=18, x=window.width // 2 - 100, y=window.height // 2 - 40, anchor_x='right')
        self.port_input = TextInput(window.width // 2 - 90, window.height // 2 - 55, 180, 30, text='4321')

        self.host_label = Label('Host:', font_size=18, x=window.width // 2 - 100, y=window.height // 2 - 80, anchor_x='right')
        self.host_input = TextInput(window.width // 2 - 90, window.height // 2 - 95, 180, 30, text='localhost')

        self.create_button = Button(window.width // 2 - 110, window.height // 2 - 160, 100, 40, 'Create', self.create_game)
        self.join_button = Button(window.width // 2 + 10, window.height // 2 - 160, 100, 40, 'Join', self.join_game)

    def create_game(self):
        seed = self.seed_input.text
        port = self.port_input.text
        if self.create_game_callback:
            self.create_game_callback(seed, port)

    def join_game(self):
        seed = self.seed_input.text
        port = self.port_input.text
        host = self.host_input.text
        if self.join_game_callback:
            self.join_game_callback(seed, port, host)

    def draw(self):
        self.title.draw()
        self.seed_label.draw()
        self.seed_input.draw()
        self.port_label.draw()
        self.port_input.draw()
        self.host_label.draw()
        self.host_input.draw()
        self.create_button.draw()
        self.join_button.draw()

    def on_mouse_press(self, x, y, button, modifiers):
        self.seed_input.on_mouse_press(x, y, button, modifiers)
        self.port_input.on_mouse_press(x, y, button, modifiers)
        self.host_input.on_mouse_press(x, y, button, modifiers)
        self.create_button.on_mouse_press(x, y, button, modifiers)
        self.join_button.on_mouse_press(x, y, button, modifiers)

    def on_text(self, text):
        self.seed_input.on_text(text)
        self.port_input.on_text(text)
        self.host_input.on_text(text)

    def on_key_press(self, symbol, modifiers):
        self.seed_input.on_key_press(symbol, modifiers)
        self.port_input.on_key_press(symbol, modifiers)
        self.host_input.on_key_press(symbol, modifiers)

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

        self.port_label.x = width // 2 - 100
        self.port_label.y = height // 2 - 40
        self.port_input.x = width // 2 - 90
        self.port_input.y = height // 2 - 55
        self.port_input.rectangle.x = width // 2 - 90
        self.port_input.rectangle.y = height // 2 - 55
        self.port_input.label.x = width // 2 - 85
        self.port_input.label.y = height // 2 - 40

        self.host_label.x = width // 2 - 100
        self.host_label.y = height // 2 - 80
        self.host_input.x = width // 2 - 90
        self.host_input.y = height // 2 - 95
        self.host_input.rectangle.x = width // 2 - 90
        self.host_input.rectangle.y = height // 2 - 95
        self.host_input.label.x = width // 2 - 85
        self.host_input.label.y = height // 2 - 80

        self.create_button.x = width // 2 - 110
        self.create_button.y = height // 2 - 160
        self.create_button.rectangle.x = width // 2 - 110
        self.create_button.rectangle.y = height // 2 - 160
        self.create_button.label.x = width // 2 - 60
        self.create_button.label.y = height // 2 - 140

        self.join_button.x = width // 2 + 10
        self.join_button.y = height // 2 - 160
        self.join_button.rectangle.x = width // 2 + 10
        self.join_button.rectangle.y = height // 2 - 160
        self.join_button.label.x = width // 2 + 60
        self.join_button.label.y = height // 2 - 140

