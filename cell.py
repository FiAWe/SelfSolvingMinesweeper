class Cell:
    """A cell in a minesweeper grid"""

    def __init__(self, x, y):
        self.loc = (x, y)
        self.is_bomb = False
        self.is_flagged = False
        self.is_revealed = False
        self.nearby_bombs = 0

        self._neighbors = []
        self._orthogonal_neighbors = []

        # TKinter references
        self.tag_id = None
        self.pixel = None
        self.canvas = None
    
    def draw_pixel(self, canvas):
        """Draw intial cell pixel on the canvas

        Args:
            canvas (tkinter.Canvas): canvas type from tkinter
        """        
        x, y = self.loc


        self.canvas = canvas
        self.pixel = canvas.create_rectangle(
            x*canvas.BOX_SIZE_X, # x start
            y*canvas.BOX_SIZE_Y, # y start
            (x+1)*canvas.BOX_SIZE_X, # x end
            (y+1)*canvas.BOX_SIZE_Y, # y end
            fill=canvas.colours["DEFAULT"], # colour
            activefill=canvas.get_lightened_color(canvas.colours["DEFAULT"]), # hover over colour
            outline=canvas.colours['CELL_BORDER'], #outline colour
            width=canvas.BORDER_WIDTH, # No outline
            activewidth=canvas.BORDER_WIDTH, #Width when hovering over
            tags=('cell', 'unrevealed') # tkinter reference tag
        )

        font_size = int( min( canvas.BOX_SIZE_X, canvas.BOX_SIZE_Y ) * 0.75 )

        y_offset = canvas.BOX_SIZE_Y/2 + (canvas.BOX_SIZE_Y - font_size)/2

        self.text = canvas.create_text(
            x*canvas.BOX_SIZE_X + canvas.BOX_SIZE_X/2, # x start
            y*canvas.BOX_SIZE_Y + y_offset, # y start
            text='', # text
            font=('Helvetica', font_size, 'bold'), # font
            fill=canvas.colours['TEXT'], # colour
            tags=('text', 'unrevealed') # tkinter reference tag
        )

        # # Assign tag 'cell', 'unrevealed' to this pixel
        # self.canvas.addtag_withtag('cell', self.pixel)
        # self.canvas.addtag_withtag('unrevealed', self.pixel)

        if self.is_bomb:
            self.canvas.addtag_withtag('bomb', self.pixel)

        # print(self.tag_id)
        return self.pixel

    def recolour(self, fill_color=None, activefill=True):
        if fill_color is None or fill_color == 'DEFAULT':
            fill_color = self.canvas.colours["DEFAULT"]
        if activefill:
            lcolor = self.canvas.get_lightened_color(fill_color)
        else:
            lcolor = fill_color
        self.canvas.itemconfig(self.pixel, fill=fill_color, activefill=lcolor)

    @property
    def neighbors(self):
        return self._neighbors

    @neighbors.setter
    def neighbors(self, neighbors):
        self._neighbors = neighbors
        bomb_count = 0
        for neighbor in neighbors:
            if neighbor.is_bomb:
                bomb_count += 1
        self.nearby_bombs = bomb_count

        # # orthogonals
        # self._orthogonal_neighbors = []
        # for neighbor in neighbors:
        #     if neighbor.loc[0] == self.loc[0] or neighbor.loc[1] == self.loc[1]:
        #         self._orthogonal_neighbors.append(neighbor)

    def left_clicked(self):
        """Left click action on cell

        If cell is not revealed, do nothing.
        If cell is revealed and number_flagged == nearby_bombs, reveal all neighbors
        If cell is revealed and number_flagged != nearby_bombs, do nothing
        """

        if not self.is_revealed:
            return False
        
        number_flagged = 0
        for neighbor in self.neighbors:
            if neighbor.is_flagged:
                number_flagged += 1

        if number_flagged != self.nearby_bombs:
            return False
        
        for neighbor in self.neighbors:
            nr = neighbor.double_clicked()
            if nr:
                return nr
            
        return False
        

    def right_clicked(self):
        """Right click action on cell

        If cell is not revealed, reverse is_flagged
        If cell is revealed, do nothing
        """

        self.flag()

    def double_clicked(self):
        """Double click action on cell

        If cell is revealed, do nothing
        if cell is not revealed and is flagged, do nothing
        if cell is not revealed and is not flagged, reveal self
        """

        if self.is_revealed:
            return False
        
        if self.is_flagged:
            return False
        
        return self.reveal(clicked=True)

    def reveal(self, clicked=False):
        """Reveal cell

        If cell is not revealed, reveal self
        If cell is revealed, do nothing

        If cell is bomb, return True else return False
        """

        if self.is_revealed:
            return False
        
        self.is_revealed = True
        self.recolour_revealed()

        # Remove tags 'unrevealed' and add 'revealed'
        self.canvas.dtag(self.pixel, 'unrevealed')
        self.canvas.dtag(self.text, 'unrevealed')
        self.canvas.addtag_withtag('revealed', self.pixel)
        self.canvas.addtag_withtag('revealed', self.text)

        if self.is_bomb:
            return True
        
        if self.nearby_bombs == 0:
            to_reveal = [n for n in self.neighbors if not n.is_revealed]
            if clicked:
                print('Revealing neighbors')
                while to_reveal:
                    neighbor = to_reveal.pop()
                    if neighbor.is_revealed:
                        continue
                    new_reveals = neighbor.reveal()
                    if new_reveals:
                        to_reveal.extend(new_reveals)
            else:
                return to_reveal
        
        return False
        
    def recolour_revealed(self):
        """Recolour cell to revealed colour"""

        if self.is_bomb:
            new_colour=self.canvas.colours["Bomb"]
            self.recolour(fill_color=new_colour, activefill=False)
        elif self.nearby_bombs > 0:
            if self.canvas.colour_revealed:
                # get colour from self.canvas.colours
                new_colour = self.canvas.colours[str(self.nearby_bombs)]
            else:
                new_colour = self.canvas.colours["0"]

            self.recolour(fill_color=new_colour, activefill=False)
        else:
            new_colour = self.canvas.colours["0"]
            self.recolour(fill_color=new_colour, activefill=True)

        # Change text
        if self.is_bomb:
            self.canvas.itemconfig(self.text, text='💣')
        else:
            if self.nearby_bombs == 0:
                display_text = ''
            else:
                display_text = self.nearby_bombs
            if self.canvas.colour_revealed:
                text_colour = self.canvas.colours['TEXT']
                self.canvas.itemconfig(self.text, text=display_text, fill=text_colour)
            else:
                text_colour = self.canvas.colours[str(self.nearby_bombs)]
                self.canvas.itemconfig(self.text, text=display_text, fill=text_colour)

    def flag(self):

        if self.is_revealed:
            return False
        
        self.is_flagged = not self.is_flagged

        if self.is_flagged:
            self.recolour(fill_color='DEFAULT', activefill=False)
            self.canvas.itemconfig(self.text, text='🚩', fill=self.canvas.colours['Bomb'])
            self.canvas.addtag_withtag('flagged', self.pixel)
        else:
            self.recolour()
            self.canvas.itemconfig(self.text, text='', fill=self.canvas.colours['TEXT'])
            self.canvas.dtag(self.pixel, 'flagged')

        return True
    
    def update_color(self):
        """
        If cell is revealed, recolour to revealed colour
        If cell is not revealed, recolour to unrevealed colour (default)
        """

        if self.is_revealed:
            self.recolour_revealed()
        else:
            if self.is_flagged:
                self.recolour(fill_color='DEFAULT', activefill=False)
            else:
                self.recolour(fill_color='DEFAULT', activefill=True)

    def __repr__(self):
        return f'Cell(@{self.loc})'
    
    def __str__(self):
        return f'Cell(@{self.loc})'
    
    def info(self):
        return f'Cell(@{self.loc}, bomb={self.is_bomb}, flagged={self.is_flagged}, revealed={self.is_revealed}, nearby_bombs={self.nearby_bombs}, neighbors={self.neighbors})'
