def factorial(n):
    """Calculate factorial of n using recursion."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

if __name__ == "__main__":
    print(f"5! = {factorial(5)}")
