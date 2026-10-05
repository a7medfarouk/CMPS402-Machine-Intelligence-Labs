from typing import Any, Dict, List
import utils


def word_histogram(text: str) -> dict:
    '''
    This function takes a string and returns a dictionary containing
    each word and its frequency in the string.
    
    A word histogram counts how many times each word appears.
    Assume words are separated by spaces and the comparison is case-sensitive.
    
    Example:
    word_histogram("cat dog cat") -> {"cat": 2, "dog": 1}
    '''
    # TODO: ADD YOUR CODE HERE
    separated_words : List = text.split()
    word_histogram_dict : Dict = dict()
    for word in separated_words:
        if (word_histogram_dict.get(word) == None):
            word_histogram_dict[word] = 1
        else: 
            word_histogram_dict[word] += 1
    return word_histogram_dict