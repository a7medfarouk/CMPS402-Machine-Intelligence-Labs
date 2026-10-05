from typing import Any, Set, Tuple
from grid import Grid
import utils


def most_frequent_item(grid: Grid):
    '''
    This function finds the most frequently occurring value in a Grid.

    Returns:
      Any: the most repeated value in the grid.
           If multiple values have the same frequency, any one may be returned.
           If the grid is empty, return None.
    '''
    # TODO: ADD YOUR CODE HERE
    width : int = grid.width
    height : int = grid.height
    frequency_dict : dict = dict()
    if width == 0 or height == 0:
      return None
    else:
      for i in range(width):
        for j in range (height):
          value : int = grid[i,j]
          if(frequency_dict.get(value) is None):
            frequency_dict[value] = 1
          else:
            frequency_dict[value] += 1
      most_frequent = max(frequency_dict, key=frequency_dict.get)
    return most_frequent
