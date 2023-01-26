import tkinter as tk
from tkinter import colorchooser
import grid
from colour import Color
from copy import deepcopy
import time
import threading
import queue
import json

class MapView(tk.Canvas):

    SCROLL_DELTA = 0.75 # How much each wheel click should zoom in/out
    BOX_SIZE_X = 20 # Tkinter box size in pixels
    BOX_SIZE_Y = 20 # Tkinter box size in pixels
    TEXT_SIZE = min(BOX_SIZE_X, BOX_SIZE_Y)*0.5
    TEXT_STYLE = 'Helvetica'
    BORDER_WIDTH = 2

    with open('colour_config.json') as f:
        colours = json.load(f)
    colours = {
        key: Color(value)
        for key, value in colours.items()
    }

    MODE_TOGGLE = False
    colour_config_window = None
    options_window = None

    def __init__(self, root, grid_params=(38, 56, None), colour_revealed=True, **kwargs):

        self.root = root

        # Calculate window size
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        print(f'screen width: {screen_width}')
        print(f'screen height: {screen_height}')

        required_width = grid_params[0] * self.BOX_SIZE_X
        required_height = grid_params[1] * self.BOX_SIZE_Y

        print(f'required width: {required_width}')
        print(f'required height: {required_height}')

        if required_width > screen_width:
            required_width = screen_width
        if required_height > screen_height:
            required_height = screen_height

        width=required_width
        height=required_height

        super(MapView, self).__init__(
            root,
            background=self.colours['BACKGROUND'],
            width=width,
            height=height,
            **kwargs
        )
        self.map_imscale = 1.0
        self.map_drag_x = 0
        self.map_drag_y = 0
        self.map_scale_x = 0
        self.map_scale_y = 0

        self.colour_revealed = colour_revealed
        self.grid_params = grid_params

        self.game_over_window = None
        self.new_game()

    def bind_keys(self, mode='game', bind_method='bind_all'):
        key_bindings = {
            'always': {
                "<space>": self.move_mode_toggle,
                "<c>": self.reconfigure_colors,
                "<Control-q>": self.quit
            },
            'game': {
                # Bind cell clicks
                '<Button-1>': self.cell_left_click,
                '<Button-3>': self.cell_right_click,
                '<Double-Button-1>': self.cell_double_click
            },
            'move_mode_toggle': {
                '<Button-1>': self.mouse_scan_mark,
                '<B1-Motion>': self.mouse_drag_to
            },
            'move': {
                # Scroll
                "<Button-4>": self.wheel,
                "<Button-5>": self.wheel,
                # Drag with middle mouse button
                # Middle
                "<Button-2>": self.mouse_scan_mark,
                "<B2-Motion>": self.mouse_drag_to
            }
        }

        assert mode in key_bindings.keys(), f'Invalid mode: {mode}'

        if bind_method == 'bind_all':
            for key, command in key_bindings[mode].items():
                # self.bind_all(key, self.rft(command))
                self.bind_all(key, command)
        elif bind_method == 'bind':
            for key, command in key_bindings[mode].items():
                self.bind(key, command)
        elif bind_method == 'unbind_all':
            for key in key_bindings[mode].items():
                self.unbind_all(key)
        elif bind_method == 'unbind':
            for key in key_bindings[mode].items():
                self.unbind(key)
        else:
            raise ValueError('Invalid bind_method')

    def mouse_scan_mark(self, event):
        self.scan_mark(event.x, event.y)

    def mouse_drag_to(self, event):
        self.scan_dragto(event.x, event.y, gain=1)

    # Bind movement to mouse when shift is pressed
    def move_mode_toggle(self):
        print('Mode toggled')
        if self.MODE_TOGGLE:
            self.MODE_TOGGLE = False
            # Unbind movement
            self.bind_keys(mode='move_mode_toggle', bind_method='unbind_all')
            self.bind_keys(mode='game', bind_method='bind_all')
            
        else:
            self.MODE_TOGGLE = True
            # Unbind cell click
            self.bind_keys(mode='game', bind_method='unbind_all')
            self.bind_keys(mode='move_mode_toggle', bind_method='bind')

    def wheel(self, event):
        ''' Zoom with mouse wheel '''
        scale = 1.0
        min_scroll = 0.5
        max_scroll = 10

        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if (event.num == 5 or event.delta == -120) and\
           (self.map_imscale > min_scroll):
            scale   *= self.SCROLL_DELTA
            self.map_imscale *= self.SCROLL_DELTA

        if (event.num == 4 or event.delta == 120)and\
           (self.map_imscale < max_scroll):
            scale   /= self.SCROLL_DELTA
            self.map_imscale /= self.SCROLL_DELTA
        
        scaled_border_width = self.map_imscale * self.BORDER_WIDTH
        scaled_text_size = int(self.map_imscale * self.TEXT_SIZE)
        new_font = (self.TEXT_STYLE, scaled_text_size, 'bold')

        # Rescale all canvas objects
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        # Re-assign border width of all objects
        self.itemconfig('cell', width=scaled_border_width)
        self.itemconfig('text', font=new_font)

        self.map_scale_x, self.map_scale_y = x, y

        self.scale('all', x, y, scale, scale)

        print(f'zoom: {self.map_imscale}')
        # self.show_image()
        self.configure(scrollregion=self.bbox('all'))

    def cell_left_click(self, event):
        current_list = self.find_withtag('current')
        if not current_list:
            print('No current tag')
            return
        elif len(current_list) > 1:
            print(f'Multiple current tags: {current_list}')
        tag = current_list[0]
        print(self.gettags(tag))
        game_over = self.ms_grid.cell_left_click(tag)
        if game_over:
            self.game_over()
        elif self.ms_grid.check_win():
            self.game_won()

    def cell_right_click(self, event):
        current_list = self.find_withtag('current')
        if not current_list:
            print('No current tag')
            return
        tag = current_list[0]
        print(self.gettags(tag))
        self.ms_grid.cell_right_click(tag)

    def cell_double_click(self, event):
        current_list = self.find_withtag('current')
        if not current_list:
            print('No current tag')
            return
        tag = current_list[0]
        print(self.gettags(tag))
        game_over = self.ms_grid.cell_double_click(tag)
        if game_over:
            self.game_over()
        elif self.ms_grid.check_win():
            self.game_won()
    
    def game_over(self):
        # If game over:
        # Rebind keys
        # pop up game over window

        # Game over window states:
        # 1. Game over
        # 2. % of cells revealed
        # 3. bombs left

        # Create game over window
        self.game_over_window = tk.Toplevel(self)
        self.game_over_window.title('Game Over')
        self.game_over_window.geometry('300x300')
        self.game_over_window.resizable(False, True)
        
        # Create game over label
        self.game_over_label = tk.Label(self.game_over_window, text='Game Over')

        # Game Over Info
        total_cells = self.ms_grid.rows * self.ms_grid.cols
        cells_revealed = self.ms_grid.cells_revealed()
        cells_revealed_percent = cells_revealed / total_cells * 100
        self.game_over_info = tk.Label(self.game_over_window, text=f'{cells_revealed_percent:.2f}% of cells revealed')
        

        bombs_left = self.ms_grid.bombs_left()
        self.bombs_left_info = tk.Label(self.game_over_window, text=f'{bombs_left} bombs left')

        # Two Buttons: New Game, Quit
        self.new_game_button = tk.Button(self.game_over_window, text='New Game', command=self.new_game)

        self.quit_button = tk.Button(self.game_over_window, text='Quit', command=self.quit)

        # Pack widgets
        self.game_over_label.pack()
        self.game_over_info.pack()
        self.bombs_left_info.pack()
        self.new_game_button.pack()
        self.quit_button.pack()

    def game_won(self):
        # If game won:
        # Rebind keys
        # pop up game won window

        # Game won window states:
        # 1. Game won
        # 2. % of cells revealed
        # 3. bombs left

        # Create game won window
        self.game_won_window = tk.Toplevel(self)
        self.game_won_window.title('Game Won')
        self.game_won_window.geometry('300x150')
        self.game_won_window.resizable(False, True)
        
        # Create game won label
        self.game_won_label = tk.Label(self.game_won_window, text='Game Won!')

        # Game Won Info
        total_cells = self.ms_grid.rows * self.ms_grid.cols
        cells_revealed_percent = 100
        self.game_won_info = tk.Label(self.game_won_window, text=f'{cells_revealed_percent:.2f}% of cells determined!')
        

        bombs_left = 0
        self.bombs_left_info = tk.Label(self.game_won_window, text=f'{bombs_left} bombs left!')

        # Two Buttons: New Game, Quit
        self.new_game_button = tk.Button(self.game_won_window, text='New Game', command=self.new_game)

        self.quit_button = tk.Button(self.game_won_window, text='Quit', command=self.quit)

        # Pack widgets
        self.game_won_label.pack()
        self.game_won_info.pack()
        self.bombs_left_info.pack()
        self.new_game_button.pack()
        self.quit_button.pack()


    def new_game(self):
        if self.game_over_window:
            self.game_over_window.destroy()
        # Destroy all canvas objects
        self.delete('all')

        rows, columns, bombs = self.grid_params
        if bombs is None:
            bombs = int(rows * columns * 0.1)
        
        # Create options window
        # Options window has entry boxes for rows, columns, bombs
        # Then a button to start game

        # Create options window
        self.options_window = tk.Toplevel(self, bg='white')
        self.options_window.title('Options')
        self.options_window.geometry('300x150')
        self.options_window.resizable(False, False)

        # Create options window labels
        self.rows_label = tk.Label(self.options_window, text='Rows', )
        self.columns_label = tk.Label(self.options_window, text='Columns')
        self.bombs_label = tk.Label(self.options_window, text='Bombs')

        # Create options window entry boxes
        self.rows_entry = tk.Entry(self.options_window)
        self.rows_entry.insert(0, rows)
        self.columns_entry = tk.Entry(self.options_window)
        self.columns_entry.insert(0, columns)
        self.bombs_entry = tk.Entry(self.options_window)
        self.bombs_entry.insert(0, bombs)

        # Create options window buttons
        self.start_button = tk.Button(self.options_window, text='Start', command=self.start_game)

        # Pack widgets
        self.rows_label.grid(row=0, column=0)
        self.rows_entry.grid(row=0, column=1)
        self.columns_label.grid(row=1, column=0)
        self.columns_entry.grid(row=1, column=1)
        self.bombs_label.grid(row=2, column=0)
        self.bombs_entry.grid(row=2, column=1)
        self.start_button.grid(row=3, column=0, columnspan=2)

        # Bring options window to front
        self.options_window.lift()
        # Set focus to options window
        self.options_window.focus_force()

    def start_game(self):

        # Get grid params from entry boxes
        rows = int(self.rows_entry.get())
        columns = int(self.columns_entry.get())
        bombs = int(self.bombs_entry.get())

        # Set grid params
        self.grid_params = (rows, columns, bombs)

        if self.options_window:
            self.options_window.destroy()

        ms_grid = grid.Grid(rows, columns, bombs, self)
        self.ms_grid = ms_grid

        self.bind_keys(mode='move', bind_method='bind')
        self.bind_keys(mode='game', bind_method='bind_all')
        self.bind_keys(mode='always', bind_method='bind_all')

    def quit(self) -> None:
        return super().quit()
    
    def reconfigure_colors(self):
        """Open color config window for user to change colors
        Colour config option has a row per relevent type of object
        Each row displays the name, current color, and a button to change color

        """

        # Delete old window if it exists
        if self.colour_config_window:
            self.colour_config_window.destroy()

        colour_labels = self.colours.keys()

        self.colour_config_window = tk.Toplevel(self)
        self.colour_config_window.title('Colour Config')

        # Define window size
        y_size = 35 * len(colour_labels) + 50
        x_size = 300
        geometry = f'{x_size}x{y_size}'

        self.colour_config_window.geometry(geometry)
        self.colour_config_window.resizable(False, True)

        self.colour_config_label = tk.Label(self.colour_config_window, text='Colour Config')
        self.colour_config_label.pack()

        self.colour_config_frame = tk.Frame(self.colour_config_window)
        self.colour_config_frame.pack()
        # Create rows for each colour

        self.colour_config_rows = []
        for i, colour_label in enumerate(colour_labels):
            current_color = self.colours[colour_label]

            colour_config_row = tk.Frame(self.colour_config_frame)
            colour_config_row.pack()
            self.colour_config_rows.append(colour_config_row)
            
            # Make copiable
            colour_config_label = tk.Label(colour_config_row, text=colour_label)
            colour_config_label.grid(row=i, column=0)

            # Text colour should be the opposite of the background
            text_colour = deepcopy(current_color)
            current_luminance = text_colour.get_luminance()
            if current_luminance > 0.5:
                text_colour.set_luminance(0)
            else:
                text_colour.set_luminance(1)

            colour_config_color = tk.Label(colour_config_row, text=current_color, bg=current_color, fg=text_colour)
            colour_config_color.grid(row=i, column=1)

            colour_config_button = tk.Button(colour_config_row, text='Change Color', command=lambda colour_label=colour_label, colour_config_color=colour_config_color, current_color=current_color: self.change_color(colour_label, colour_config_color, current_color))
            colour_config_button.grid(row=i, column=2)


        # Close button
        self.colour_config_close_button = tk.Button(self.colour_config_window, text='Close', command=self.colour_config_window_close)

        self.colour_config_close_button.pack()

    def colour_config_window_close(self):
        # Destroy window, write new colors to config file and update colors
        self.colour_config_window.destroy()

        # Write new colors to config file
        to_write = {
            k: str(v) for k, v in self.colours.items()
        }
        print('Writing to config file')
        with open('colour_config.json', 'w') as f:
            json.dump(to_write, f, indent=4)

        # Update colors
        self.ms_grid.update_colors()

        # Find all canvas objects with tag 'text' and update color
        self.itemconfig('text', fill=self.colours['TEXT'])

        # Find all canvas objects with tag 'cell' and border color
        self.itemconfig('cell', outline=self.colours['CELL_BORDER'])

        # Update the background color of the canvas
        self.config(bg=self.colours['BACKGROUND'])



    def change_color(self, colour_label, colour_config_color, prev_color=None):
        # Open color picker
        # Change color of label
        # Update color of object

        color = colorchooser.askcolor(title=f'Choose Color for {colour_label}', initialcolor=prev_color)

        # New text color should be the opposite of the background
        text_colour = Color(color[1])
        current_luminance = text_colour.get_luminance()
        if current_luminance > 0.5:
            text_colour.set_luminance(0)
        else:
            text_colour.set_luminance(1)

        # Change color of label
        colour_config_color.config(text=color[1], bg=color[1], fg=text_colour)

        # Update color of object
        self.colours[colour_label] = Color(color[1])


    def run_func_threaded(self, func, process_after=100):
        """Wrap function in threaded task manager linked to canvas thread
        queue

        Args:
            func (function): function to be wrapped
            process_after (int, optional): ms after which to process queue.
                                           Defaults to 100.
        """        

        def wrapper(*args, **kwargs):
            self.queue = queue.Queue()
            ThreadedTask(
                self.queue, 
                func,
                args=args,
                kwargs=kwargs
                ).start()
            self.master.after(process_after, self.process_queue)
        return wrapper

    def run_func(self, func):
        """Wrap function in threaded task manager linked to canvas thread
        queue

        Args:
            func (function): function to be wrapped
            process_after (int, optional): ms after which to process queue.
                                           Defaults to 100.
        """        

        def wrapper(*args, **kwargs):
            func()

        return wrapper
    
    rft = run_func_threaded
    rf = run_func

    def process_queue(self):
        try:
            self.queue.get(0)
            # Show result of the task if needed
            # self.update_idletasks()
        except queue.Empty:
            self.master.after(100, self.process_queue)

    @staticmethod
    def get_lightened_color(color, factor=0.5):
        """Return color with luminence factor fraction from current
        luminence to full lumincence

        Args:
            color (Color): [colour.Color to be lightenened]
            factor (float, optional): colour will be lightened by distance to 
            full luminance multipleid by the factor. Recomended val 0 -> 1.
            Defaults to 0.5.

        Returns:
            Color: lightened colour
        """              

        assert isinstance(color, Color)

        light_color = deepcopy(color)
        default_lum = color.luminance
        new_lum = default_lum + factor*(1-default_lum)
        light_color.luminance = new_lum

        return light_color


class ThreadedTask(threading.Thread):
    def __init__(self, queue, command, args={}, kwargs={}):
        threading.Thread.__init__(self)
        self.queue = queue
        self.command = command
        self.kwargs = kwargs
    def run(self, *args, **kwargs):
        self.command(*args, **self.kwargs) 
        self.queue.put("Task finished")

master = tk.Tk()
mapview = MapView(master) #, (200,200, None))
mapview.pack(fill=tk.BOTH, expand=tk.YES)
master.mainloop()