"""sample_module.parsing.decor

All the decoraters that help create a sample output
"""

def decor(func):
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner