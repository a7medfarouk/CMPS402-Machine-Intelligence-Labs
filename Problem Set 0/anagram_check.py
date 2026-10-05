import utils

def anagram_check(s1: str, s2: str) -> bool:
    '''
    This function takes two strings and returns whether they are anagrams of each other or not.
    An anagram is formed when two strings contain exactly the same letters in any order.
    For example, "listen" and "silent" are anagrams, while "hello" and "world" are not.
    Assume the comparison is case-sensitive.
    '''
    # TODO: ADD YOUR CODE HERE
    sorted_s1 : str = sorted(s1)
    sorted_s2 : str = sorted(s2)
    if (sorted_s1 == sorted_s2):
        return True
    else :
        return False