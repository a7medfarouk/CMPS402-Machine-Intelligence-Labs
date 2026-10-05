from typing import List
import utils

def score_to_grade(score: int) -> str:
    '''
    Convert a numeric score into a letter grade.
    '''
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def calculate_exam_score(questions: list[dict], answers: list[bool]) -> tuple[int, str]:
    '''
    This function calculates the student's **exam score** and returns **both**:
    1. The total numeric score (sum of points for correctly answered questions).
    2. The corresponding letter grade (using score_to_grade).

    Each question has:
      - "points": how many marks it is worth.
      - The student’s answer is True if correct, False if incorrect.

    Example:
        questions = [{"points": 50}, {"points": 30}, {"points": 20}]
        answers   = [True, True, False]

        Raw score = 50 + 30 = 80
        Grade     = "B"

        Output → (80, "B")
    '''
    raw_score : int = 0
    # TODO: ADD YOUR CODE HERE
    for index , answer in enumerate(answers):
        if(answer == True) : 
            raw_score += questions[index]["points"]
    grade = score_to_grade(raw_score)
    return raw_score, grade
    