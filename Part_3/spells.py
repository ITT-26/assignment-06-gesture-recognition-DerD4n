"""
Spell definitions and combat resolution for Spell Duel.
"""

import random

# ----------------------------------------------------------------
# Spell table: gesture class -> spell definition
# ----------------------------------------------------------------
# Elemental cycle: fire > earth > lightning > water > fire
# shield (arcane) blocks/reduces incoming damage on the turn it's cast
# holy (light) is neutral, deals damage AND heals the caster a little
# my ideas code for the spell effects are ai generated 

SPELLS = {
    "arrow": {
        "name": "Fire Bolt",
        "element": "fire",
        "base_damage": 22,
        "heal": 0,
        "shield": 0,
        "art_key": "fire",
    },
    "triangle": {
        "name": "Stone Spike",
        "element": "earth",
        "base_damage": 18,
        "heal": 0,
        "shield": 0,
        "art_key": "earth",
    },
    "x": {
        "name": "Lightning Strike",
        "element": "lightning",
        "base_damage": 24,
        "heal": 0,
        "shield": 0,
        "art_key": "lightning",
    },
    "check": {
        "name": "Water Surge",
        "element": "water",
        "base_damage": 18,
        "heal": 0,
        "shield": 0,
        "art_key": "water",
    },
    "star": {
        "name": "Holy Nova",
        "element": "light",
        "base_damage": 14,
        "heal": 8,
        "shield": 0,
        "art_key": "holy",
    },
    "circle": {
        "name": "Aegis Shield",
        "element": "arcane",
        "base_damage": 0,
        "heal": 0,
        "shield": 18,
        "art_key": "shield",
    },
}

SPELL_GESTURES = list(SPELLS.keys())

# Elemental beats-table: attacker_element -> defender_element it counters
BEATS = {
    "fire": "earth",
    "earth": "lightning",
    "lightning": "water",
    "water": "fire",
}
ELEMENT_BONUS_MULT = 1.5
ELEMENT_RESIST_MULT = 0.6   # damage dealt when on the losing side of the cycle

# Confidence thresholds for cast quality
CONF_MIN_THRESHOLD = 0.40
CONF_MAX_THRESHOLD = 0.90 

def cast_quality(confidence):
    """
    calculates a smooth multiplier between 0.0 and 1.0.
    Returns (quality_string, power_multiplier).
    """
    if confidence < CONF_MIN_THRESHOLD:
        return "fizzle", 0.0
    
    if confidence >= CONF_MAX_THRESHOLD:
        return "perfect!", 1.0
    
    # Linear scaling between MIN and MAX
    mult = (confidence - CONF_MIN_THRESHOLD) / (CONF_MAX_THRESHOLD - CONF_MIN_THRESHOLD)
    
    # Dynamic text quality for the combat log
    if mult < 0.4:
        quality = "weak"
    elif mult < 0.9:
        quality = "good"
    else:
        quality = "powerful"
        
    return quality, mult


def elemental_multiplier(attacker_element, defender_element):
    """Returns damage multiplier based on the elemental beats-cycle."""
    if attacker_element in ("arcane", "light") or defender_element in ("arcane", "light"):
        return 1.0
    if BEATS.get(attacker_element) == defender_element:
        return ELEMENT_BONUS_MULT
    if BEATS.get(defender_element) == attacker_element:
        return ELEMENT_RESIST_MULT
    return 1.0


def resolve_cast(spell_key, confidence, defender_shield=0):
    """
    Resolve a single spell cast.

    Returns a dict describing the outcome:
        {
            "spell_key": str,
            "spell_name": str,
            "quality": "full" | "half" | "fizzle",
            "raw_damage": int,
            "final_damage": int,   # after elemental mult and shield reduction
            "heal": int,
            "new_shield": int,     # shield value this caster now has active (if circle)
            "element_mult": float,
        }
    """
    spell = SPELLS[spell_key]
    quality, mult = cast_quality(confidence)

    raw_damage = int(spell["base_damage"] * mult)
    heal = int(spell["heal"] * mult)
    new_shield = int(spell["shield"] * mult)

    return {
        "spell_key": spell_key,
        "spell_name": spell["name"],
        "element": spell["element"],
        "quality": quality,
        "confidence": confidence,
        "raw_damage": raw_damage,
        "heal": heal,
        "new_shield": new_shield,
    }


def apply_damage(outcome, defender_element, defender_shield):
    """
    Given a cast outcome and the defender's current state, compute final
    damage after elemental multiplier and shield absorption.

    Returns (final_damage, shield_remaining_after_absorb).
    """
    mult = elemental_multiplier(outcome["element"], defender_element)
    dmg = outcome["raw_damage"] * mult

    absorbed = min(dmg, defender_shield)
    dmg_after_shield = dmg - absorbed
    shield_remaining = defender_shield - absorbed

    return int(round(dmg_after_shield)), int(round(shield_remaining)), mult


# ----------------------------------------------------------------
# Simple AI opponent is ai generated
# ----------------------------------------------------------------

def ai_choose_spell(ai_hp, player_last_element=None):
    """
    Very simple heuristic AI:
    - If HP is low (<30%), favor Holy Nova for the self-heal.
    - If it knows the player's last element, try to counter it.
    - Otherwise pick randomly.
    """
    if ai_hp <= 30 and random.random() < 0.6:
        return "star"

    if player_last_element:
        counters = [k for k, v in SPELLS.items() if BEATS.get(v["element"]) == player_last_element]
        if counters and random.random() < 0.5:
            return random.choice(counters)

    return random.choice(SPELL_GESTURES)


def ai_simulated_confidence():
    """AI always 'casts' with a randomized but generally decent confidence."""
    return random.uniform(0.55, 0.97)