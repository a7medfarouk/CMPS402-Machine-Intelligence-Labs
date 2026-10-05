from typing import Tuple, List, Set
import utils

'''
    The DecipherResult is the type defintion for a tuple containing:
    - The deciphered text (string).
    - The shift of the cipher (non-negative integer).
        Assume that the shift is always to the right (in the direction from 'a' to 'b' to 'c' and so on).
        So if you return 1, that means that the text was ciphered by shifting it 1 to the right, and that you deciphered the text by shifting it 1 to the left.
    - The number of words in the deciphered text that are not in the dictionary (non-negative integer).
'''
DechiperResult = Tuple[str, int, int]

def caesar_dechiper(ciphered: str, dictionary: List[str]) -> DechiperResult:
    '''
        This function takes the ciphered text (string)  and the dictionary (a list of strings where each string is a word).
        It should return a DechiperResult (see above for more info) with the deciphered text, the cipher shift, and the number of deciphered words that are not in the dictionary. 
    '''
    #TODO: ADD YOUR CODE HERE
    cipher_shift : int = 0
    deciphered_word : str
    min_unknown_word_count = float('inf')
    cipher_list : List = ciphered.split()
    optimal_deciphered_list : List = []
    dictionary_set : Set = set(dictionary)
    for i in range(26):
        
        unknown_word_count : int = 0
        deciphered_word_list : List = []
        
        for word in cipher_list:
            
            deciphered_word = ""
            
            for char in word:
                deciphered_word += chr((ord(char)- ord('a') - i) % 26 + ord('a'))
                
            if deciphered_word not in dictionary_set : unknown_word_count += 1
            
            deciphered_word_list.append(deciphered_word)
            
        if unknown_word_count < min_unknown_word_count:
            min_unknown_word_count = unknown_word_count
            cipher_shift = i
            optimal_deciphered_list = deciphered_word_list
            
    deciphered_text = " ".join(optimal_deciphered_list)
    deciphered_text.strip()
    
    return deciphered_text, cipher_shift, min_unknown_word_count