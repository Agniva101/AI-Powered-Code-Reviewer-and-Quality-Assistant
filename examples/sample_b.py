"""Example module demonstrating generator and exception handling functions."""
def generator_example(n):
    """
    Generate a sequence of integers from 0 to n-1.
    
    Args:
        n (int): The upper limit of the sequence.
    
    Yields:
        int: The next integer in the sequence.
    """
    for i in range(n):
        yield i

def raises_example(x):
    """
    Double the input value and raise an exception for negative inputs.
    
    Args:
        x (int): The input value to be doubled or checked for negativity.
    
    Returns:
        int: The doubled input value.
    
    Raises:
        ValueError: When the input value is negative.
    """
    if x < 0:
        raise ValueError("negative")
    return x * 2
