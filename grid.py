from cell import Cell
import numpy as np

class Grid:
    """
    Grid of minesweeper cells.
    """

    def __init__(self, rows, cols, bombs=None, canvas=None, cheat_win=False):
        """
        Initialize the grid.
        """
        self.rows = rows
        self.cols = cols

        if bombs is None:
            bombs = int(rows * cols * 0.10)
        self.bomb_count = bombs
        self.bombs = []


        self.cell_array = np.empty((rows, cols), dtype=Cell)
        self._initialize_cells()

        self.tag_lookup = {}

        self.canvas = canvas
        self.cells_created = False
        self.create_grid_cells()

        if cheat_win:
            for c in self.cell_array.flatten():
                if not c.is_bomb and not c.is_revealed:
                    c.reveal(True)

    def create_grid_cells(self, canvas=None):
        """Draw all cells without refreshing view
        """        
        if canvas is None:
            canvas = self.canvas

        if not self.cells_created:
            for c in self.cell_array.flatten():
                c_tag = c.draw_pixel(canvas=canvas)
                self.tag_lookup[c_tag] = c
                t_tag = c.text
                self.tag_lookup[t_tag] = c
            self.cells_created = True
        else:
            print('cells already created for this grid')

    def update_colors(self):
        """Update the colors of all cells
        """        
        for c in self.cell_array.flatten():
            c.update_color()

    def _initialize_cells(self):
        """
        Initialize the cells in the grid.
        """
        for row in range(self.rows):
            for col in range(self.cols):
                self.cell_array[row][col] = Cell(row, col)

        # Assign bombs to random cells
        self._assign_bombs()
        print(f'Bombs at {self.bombs}')

        # Assign neighbors to each cell
        for row in range(self.rows):
            for col in range(self.cols):
                cell = self._get_cell(row, col)
                cell.neighbors = self._get_cell_neighbors(row, col)

    def _get_cell(self, row, col):
        """
        Get a cell from the grid.
        """
        return self.cell_array[row][col]

    def _get_cell_neighbors(self, row, col):
        """
        Get the neighbors of a cell.
        """
        neighbors = []
        for i in range(row - 1, row + 2):
            for j in range(col - 1, col + 2):
                if i >= 0 and i < self.rows and j >= 0 and j < self.cols:
                    neighbors.append(self._get_cell(i, j))
        return neighbors

    def _assign_bombs(self):
        """
        Assign bombs to random cells.
        """
        for bomb_cell in np.random.choice(self.cell_array.flatten(), self.bomb_count, replace=False):
            bomb_cell.is_bomb = True
            self.bombs.append(bomb_cell)

        self.bombs = sorted(self.bombs, key=lambda x: x.loc)

    def cell_left_click(self, tag):
        cell = self.tag_lookup[tag]
        print(cell)
        bomb_clicked = cell.left_clicked()

        if bomb_clicked:
            self.game_over()
            return True
        else:
            return False

    def cell_right_click(self, tag):
        cell = self.tag_lookup[tag]
        print(cell)
        cell.right_clicked()

    def cell_double_click(self, tag):
        cell = self.tag_lookup[tag]
        print(cell.info())
        bomb_clicked = cell.double_clicked()

        if bomb_clicked:
            self.game_over()
            return True
        else:
            return False
        
    def check_win(self):
        print('Checking win')
        print(f'Cells Revealed: {self.cells_revealed()}')
        print(f'Cells Total: {self.rows * self.cols}')
        print(f'Bombs: {self.bomb_count}')
        print(f'Required: {self.rows * self.cols - self.bomb_count}')
        if self.cells_revealed() == self.rows * self.cols - self.bomb_count:
            print('You Win!')
            return True
        else:
            return False

    def game_over(self):
        print('Game Over')
        # Reveal all bombs
        for bomb in self.bombs:
            bomb.reveal()

    def cells_revealed(self):
        return np.sum([c.is_revealed for c in self.cell_array.flatten()])
    
    def bombs_left(self):
        return self.bomb_count - np.sum([c.is_flagged and c.is_bomb for c in self.bombs])