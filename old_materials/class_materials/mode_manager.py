"""
Mode Manager - Central personality and behavior mode controller
Manages different interaction modes (personalities) for the LLM assistant.
"""

# Define all available modes with their personality contexts
MODES = {
    "normal": "You are a neutral and helpful assistant.",
    
    "santa": (
        "You are Santa Claus — warm, cheerful, and jolly. "
        "Always speak kindly, and sprinkle festive expressions like 'Ho ho ho!' "
        "and references to Christmas, the North Pole, elves, and reindeer when appropriate."
    ),
    
    "engineer": (
        "You are a senior software engineer — precise, technical, and detail-oriented. "
        "You prefer clear explanations with technical accuracy. "
        "You think in terms of architecture, optimization, and best practices."
    ),
    
    "teacher": (
        "You are a patient and encouraging teacher. "
        "You explain concepts step-by-step, use analogies to make things clear, "
        "and always check for understanding. You're supportive and never condescending."
    ),
    
    "pirate": (
        "You are a friendly pirate — adventurous and spirited! "
        "You speak with pirate slang (ahoy, matey, arr), reference the sea, "
        "treasure, and sailing. You're helpful but always in character."
    )
}

# Current active mode (default is "normal")
_active_mode = "normal"


def get_mode() -> str:
    """
    Get the currently active mode name.
    
    Returns:
        str: The name of the active mode (e.g., "normal", "santa")
    """
    return _active_mode


def set_mode(mode_name: str) -> bool:
    """
    Set the active mode.
    
    Args:
        mode_name: The name of the mode to activate
        
    Returns:
        bool: True if mode was set successfully, False if mode doesn't exist
    """
    global _active_mode
    
    mode_name = mode_name.lower().strip()
    
    if mode_name in MODES:
        _active_mode = mode_name
        return True
    return False


def get_mode_context() -> str:
    """
    Get the personality context string for the currently active mode.
    This is the text that will be prepended to LLM prompts.
    
    Returns:
        str: The personality description for the active mode
    """
    return MODES.get(_active_mode, MODES["normal"])


def list_available_modes() -> list:
    """
    Get a list of all available mode names.
    
    Returns:
        list: List of mode names
    """
    return list(MODES.keys())


def get_mode_description(mode_name: str) -> str:
    """
    Get the description for a specific mode.
    
    Args:
        mode_name: Name of the mode
        
    Returns:
        str: Mode description, or empty string if mode doesn't exist
    """
    return MODES.get(mode_name.lower().strip(), "")

