"""Provide core mathematical and utility functions for data processing."""
import math
def calculate_average(numbers):
    """
    Calculate the average of a list of numbers.
    
    Args:
        numbers (list): A list of numbers to calculate the average from.
    
    Returns:
        float: The average of the input numbers.
    """
    total = 0
    for n in numbers:
        total += n
    if len(numbers) == 0:
        return 0
    return total / len(numbers)

def add(a: int, b: int) -> int:
    """
    Calculate the sum of two integers.
    
    Args:
        a (int): The first integer to add.
        b (int): The second integer to add.
    
    Returns:
        int: The sum of a and b.
    """
    return a + b

class Processor:
    num: int
    def set_num(self, num: int):
        """
        Set the instance attribute 'num' to the given integer value.
        
        Args:
            num (int): The integer value to be assigned to the instance attribute 'num'.
        """
        self.num = num

    def process(self, data):
        """
        Process data items in the provided list.
        
        Args:
            data (list): A list of items to be processed.
        """
        for item in data:
            if item is None:
                continue
            print(item)
